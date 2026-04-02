package com.agent.utils;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import lombok.extern.slf4j.Slf4j;

@Slf4j
@Component
public class ApiCilent {
    private static final String[] TOKEN_KEYS = {
            "token", "accessToken", "access_token", "authToken", "jwt", "jwtToken", "authorization", "Authorization"
    };
    private static final String[] HEADER_TOKEN_KEYS = {
            "token", "authorization", "Authorization", "access-token", "access_token", "x-access-token", "jwt"
    };
    private static final String[] MESSAGE_KEYS = {
            "msg", "message", "errorMsg", "errmsg", "error_message"
    };

    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${RequestApi.url}")
    private String url;

    @Value("${external.hmdp.base-url:http://localhost:8081}")
    private String hmdpBaseUrl;

    @Value("${external.sky-take-out.base-url:http://localhost:8086}")
    private String skyTakeOutBaseUrl;

    private HttpHeaders buildDefaultJsonHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setAccept(Collections.singletonList(MediaType.APPLICATION_JSON));
        return headers;
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> requestJson(String requestUrl, HttpMethod method, Map<String, Object> requestBody) {
        Map<String, Object> response = requestJsonResponse(requestUrl, method, requestBody);
        Object respBody = response.get("body");
        if (!(respBody instanceof Map)) {
            throw new RuntimeException("External response body is empty");
        }
        return (Map<String, Object>) respBody;
    }

    private Map<String, Object> requestJsonResponse(String requestUrl, HttpMethod method, Map<String, Object> requestBody) {
        HttpEntity<?> entity = requestBody == null
                ? new HttpEntity<>(buildDefaultJsonHeaders())
                : new HttpEntity<>(requestBody, buildDefaultJsonHeaders());

        ResponseEntity<Map> response = restTemplate.exchange(requestUrl, method, entity, Map.class);
        Map<String, Object> result = new HashMap<>();
        result.put("body", response.getBody());
        result.put("headers", flattenHeaders(response.getHeaders()));
        result.put("statusCode", response.getStatusCodeValue());
        return result;
    }

    public Map<String, Object> postJson(String requestUrl, Map<String, Object> requestBody) {
        return requestJson(requestUrl, HttpMethod.POST, requestBody);
    }

    public Map<String, Object> getJson(String requestUrl) {
        return requestJson(requestUrl, HttpMethod.GET, null);
    }

    public Map<String, Object> sendHmdpCode(String phone) {
        String requestUrl = hmdpBaseUrl + "/user/code?phone=" + phone;
        return requestJson(requestUrl, HttpMethod.POST, null);
    }

    public Map<String, Object> loginHmdp(String phone, String code, String password) {
        Map<String, Object> body = new HashMap<>();
        body.put("phone", phone);
        body.put("code", code);
        body.put("password", password);
        return requestJsonResponse(hmdpBaseUrl + "/user/login", HttpMethod.POST, body);
    }

    public Map<String, Object> loginSkyTakeOut(String code) {
        Map<String, Object> body = new HashMap<>();
        body.put("code", code);
        return requestJsonResponse(skyTakeOutBaseUrl + "/user/user/login", HttpMethod.POST, body);
    }

    public String talk(String question, String userId) {
        Map<String, Object> body = new HashMap<>();
        body.put("question", question);
        body.put("user_id", userId);
        Map<String, Object> resp = postJson(buildAgentUrl("/chat"), body);
        Object result = resp.get("result");
        if (result == null) {
            log.warn("Agent /chat response does not contain result field, resp={}", resp);
            return "";
        }
        return String.valueOf(result);
    }

    public void talkStream(String question, String userId, OutputStream outputStream) {
        Map<String, Object> body = new HashMap<>();
        body.put("question", question);
        body.put("user_id", userId);

        restTemplate.execute(
                buildAgentUrl("/chat/stream"),
                HttpMethod.POST,
                request -> {
                    request.getHeaders().setContentType(MediaType.APPLICATION_JSON);
                    request.getHeaders().setAccept(Collections.singletonList(MediaType.TEXT_PLAIN));
                    request.getBody().write(objectMapper.writeValueAsBytes(body));
                    request.getBody().flush();
                },
                response -> {
                    copyResponseStream(response.getBody(), outputStream);
                    return null;
                }
        );
    }

    public Map<String, Object> bindHmdp(String phone, String code, String password) {
        return parseLoginResponse(loginHmdp(phone, code, password));
    }

    public Map<String, Object> bindSkyTakeOut(String code) {
        return parseLoginResponse(loginSkyTakeOut(code));
    }

    private Map<String, Object> parseLoginResponse(Map<String, Object> responseMeta) {
        Map<String, Object> body = asObjectMap(responseMeta.get("body"));
        Map<String, Object> data = asObjectMap(body.get("data"));
        Map<String, String> headers = asStringMap(responseMeta.get("headers"));

        String token = firstNonBlank(
                tokenFromValue(body.get("data")),
                tokenFromMap(data),
                tokenFromMap(body),
                tokenFromHeaders(headers)
        );
        Long userId = firstNonNull(
                longValue(data.get("id")),
                longValue(data.get("userId")),
                longValue(data.get("user_id")),
                longValue(body.get("id")),
                longValue(body.get("userId")),
                longValue(body.get("user_id"))
        );
        String message = firstNonBlank(messageFromMap(body), messageFromMap(data));

        if (!hasText(token)) {
            log.warn("Failed to extract token from login response. body={}, headers={}", body, headers);
        }

        Map<String, Object> result = new HashMap<>();
        result.put("token", token);
        result.put("userId", userId);
        result.put("message", message);
        result.put("raw", body);
        result.put("headers", headers);
        result.put("statusCode", responseMeta.get("statusCode"));
        return result;
    }

    private Map<String, String> flattenHeaders(HttpHeaders headers) {
        Map<String, String> result = new HashMap<>();
        if (headers == null) {
            return result;
        }
        for (Map.Entry<String, List<String>> entry : headers.entrySet()) {
            if (entry.getValue() == null || entry.getValue().isEmpty()) {
                continue;
            }
            String value = toText(entry.getValue().get(0));
            if (!hasText(value)) {
                continue;
            }
            result.put(entry.getKey(), value);
            result.put(entry.getKey().toLowerCase(), value);
        }
        return result;
    }

    private String tokenFromValue(Object value) {
        if (!(value instanceof String)) {
            return null;
        }
        return normalizeToken((String) value);
    }

    private String tokenFromMap(Map<String, Object> source) {
        for (String key : TOKEN_KEYS) {
            String value = normalizeToken(toText(source.get(key)));
            if (hasText(value)) {
                return value;
            }
        }
        return null;
    }

    private String tokenFromHeaders(Map<String, String> headers) {
        for (String key : HEADER_TOKEN_KEYS) {
            String value = normalizeToken(headers.get(key));
            if (hasText(value)) {
                return value;
            }
            value = normalizeToken(headers.get(key.toLowerCase()));
            if (hasText(value)) {
                return value;
            }
        }
        return null;
    }

    private String messageFromMap(Map<String, Object> source) {
        for (String key : MESSAGE_KEYS) {
            String value = toText(source.get(key));
            if (hasText(value)) {
                return value;
            }
        }
        return null;
    }

    private String normalizeToken(String token) {
        if (!hasText(token)) {
            return null;
        }
        String trimmed = token.trim();
        if (trimmed.regionMatches(true, 0, "Bearer ", 0, 7)) {
            return trimmed.substring(7).trim();
        }
        return trimmed;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> asObjectMap(Object value) {
        if (value instanceof Map) {
            return (Map<String, Object>) value;
        }
        return Collections.emptyMap();
    }

    private Map<String, String> asStringMap(Object value) {
        if (!(value instanceof Map)) {
            return Collections.emptyMap();
        }
        Map<?, ?> rawMap = (Map<?, ?>) value;
        Map<String, String> result = new HashMap<>();
        for (Map.Entry<?, ?> entry : rawMap.entrySet()) {
            String key = toText(entry.getKey());
            String mapValue = toText(entry.getValue());
            if (hasText(key) && hasText(mapValue)) {
                result.put(key, mapValue);
            }
        }
        return result;
    }

    private Long longValue(Object value) {
        if (value instanceof Number) {
            return ((Number) value).longValue();
        }
        String text = toText(value);
        if (!hasText(text)) {
            return null;
        }
        try {
            return Long.parseLong(text);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private boolean hasText(String value) {
        return value != null && !value.trim().isEmpty();
    }

    private String toText(Object value) {
        if (value == null) {
            return null;
        }
        String text = String.valueOf(value).trim();
        return text.isEmpty() ? null : text;
    }

    private String firstNonBlank(String... values) {
        if (values == null) {
            return null;
        }
        for (String value : values) {
            if (hasText(value)) {
                return value;
            }
        }
        return null;
    }

    private Long firstNonNull(Long... values) {
        if (values == null) {
            return null;
        }
        for (Long value : values) {
            if (value != null) {
                return value;
            }
        }
        return null;
    }

    private String buildAgentUrl(String path) {
        if (url.endsWith("/") && path.startsWith("/")) {
            return url.substring(0, url.length() - 1) + path;
        }
        if (!url.endsWith("/") && !path.startsWith("/")) {
            return url + "/" + path;
        }
        return url + path;
    }

    private void copyResponseStream(InputStream inputStream, OutputStream outputStream) throws IOException {
        byte[] buffer = new byte[1024];
        int len;
        while ((len = inputStream.read(buffer)) != -1) {
            outputStream.write(buffer, 0, len);
            outputStream.flush();
        }
    }
}
