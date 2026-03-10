package com.agent.utils;

import org.springframework.web.client.RestTemplate;
import org.springframework.beans.factory.annotation.Value;
import com.agent.entity.Chat;

import lombok.extern.slf4j.Slf4j;

import org.springframework.http.*;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class ApiCilent {
    private final RestTemplate restTemplate;
    @Value("${RequestApi.url}")
    private String url;

    public ApiCilent(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    @Async
    public String post(String question, String user_id) {
        // 1. 设置请求头
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        // 2. 构建请求体
        Chat chat = Chat.builder()
                .question(question)
                .user_id(user_id)
                .build();
        String postUrl = this.url + "/chat";
        // 3. 发送POST请求
        ResponseEntity<String> response = restTemplate.exchange(
                postUrl,
                HttpMethod.POST,
                new HttpEntity<>(chat, headers),
                String.class);
        // 4. 处理响应
        if (response.getStatusCode() == HttpStatus.OK) {
            String responseBody = response.getBody();
            log.debug("POST请求成功，响应体：{}", responseBody);
        } else {
            log.error("POST请求失败，状态码：{}", response.getStatusCode());
        }
        // 5. 返回响应体
        return response.getBody().toString();
    }
}
