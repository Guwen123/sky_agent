package com.agent.service.impl;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import javax.annotation.Resource;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import com.agent.entity.BindHmdpLoginRequest;
import com.agent.entity.BindSkyTakeOutLoginRequest;
import com.agent.entity.Result;
import com.agent.entity.User;
import com.agent.entity.UserAccountBinding;
import com.agent.mapper.UserAccountBindingMapper;
import com.agent.mapper.UserMapper;
import com.agent.service.UserService;
import com.agent.utils.ApiCilent;
import com.agent.utils.UserHolder;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;

import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
public class UserServiceImpl implements UserService {
    @Resource
    private UserMapper userMapper;
    @Resource
    private UserAccountBindingMapper userAccountBindingMapper;
    @Resource
    private ApiCilent apiCilent;
    @Resource
    private JdbcTemplate jdbcTemplate;

    @Override
    public Result detail() {
        User user = UserHolder.getUser();
        if (user == null) {
            return Result.error("\u7528\u6237\u672a\u767b\u5f55");
        }
        return Result.ok(user);
    }

    @Override
    public Result logout() {
        UserHolder.removeUser();
        return Result.ok("\u9000\u51fa\u6210\u529f");
    }

    @Override
    public Result talk(String question) {
        User user = UserHolder.getUser();
        if (user == null) {
            return Result.error("\u7528\u6237\u672a\u767b\u5f55");
        }
        String answer;
        try {
            answer = apiCilent.talk(question, user.getId().toString());
        } catch (Exception e) {
            return Result.error("\u8c03\u7528 Agent \u670d\u52a1\u5931\u8d25: " + e.getMessage());
        }
        userMapper.updateById(User.builder().id(user.getId()).updateTime(LocalDateTime.now()).build());
        return Result.ok(answer);
    }

    @Override
    public StreamingResponseBody streamTalk(String question) {
        User user = UserHolder.getUser();
        if (user == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "\u7528\u6237\u672a\u767b\u5f55");
        }

        final Long userId = user.getId();
        final String userIdText = userId.toString();

        return outputStream -> {
            try {
                apiCilent.talkStream(question, userIdText, outputStream);
                userMapper.updateById(User.builder().id(userId).updateTime(LocalDateTime.now()).build());
            } catch (Exception e) {
                try {
                    outputStream.write(("\u8c03\u7528 Agent \u670d\u52a1\u5931\u8d25: " + e.getMessage()).getBytes(StandardCharsets.UTF_8));
                    outputStream.flush();
                } catch (IOException ioException) {
                    throw new RuntimeException(ioException);
                }
            }
        };
    }

    @Override
    public Result sendHmdpCode(String phone) {
        User user = UserHolder.getUser();
        if (user == null) {
            return Result.error("\u7528\u6237\u672a\u767b\u5f55");
        }
        if (!hasText(phone)) {
            return Result.error(400, "phone \u4e0d\u80fd\u4e3a\u7a7a");
        }
        try {
            return Result.ok("\u9a8c\u8bc1\u7801\u5df2\u53d1\u9001", apiCilent.sendHmdpCode(phone));
        } catch (Exception e) {
            return Result.error("\u8c03\u7528 hmdp \u53d1\u9001\u9a8c\u8bc1\u7801\u5931\u8d25: " + e.getMessage());
        }
    }

    @Override
    public Result bindHmdp(BindHmdpLoginRequest request) {
        User user = UserHolder.getUser();
        if (user == null) {
            return Result.error("\u7528\u6237\u672a\u767b\u5f55");
        }
        if (request == null || !hasText(request.getPhone())) {
            return Result.error(400, "phone \u4e0d\u80fd\u4e3a\u7a7a");
        }

        Map<String, Object> parsed;
        try {
            parsed = apiCilent.bindHmdp(request.getPhone(), request.getCode(), request.getPassword());
        } catch (Exception e) {
            return Result.error("hmdp \u7ed1\u5b9a\u5931\u8d25: " + e.getMessage());
        }

        String token = toText(parsed.get("token"));
        Long hmdpUserId = parsed.get("userId") instanceof Number
                ? ((Number) parsed.get("userId")).longValue()
                : null;
        if (!hasText(token)) {
            String message = toText(parsed.get("message"));
            log.warn("hmdp login missing token, parsed={}", parsed);
            if (hasText(message)) {
                return Result.error("hmdp \u767b\u5f55\u672a\u8fd4\u56de token\uff0c\u63a5\u53e3\u6d88\u606f: " + message);
            }
            return Result.error("hmdp \u767b\u5f55\u672a\u8fd4\u56de token\uff0c\u8bf7\u68c0\u67e5\u5916\u90e8\u63a5\u53e3 body/header");
        }

        QueryWrapper<UserAccountBinding> wrapper = new QueryWrapper<>();
        wrapper.eq("agent_user_id", user.getId());
        UserAccountBinding binding = userAccountBindingMapper.selectOne(wrapper);
        if (binding == null) {
            binding = new UserAccountBinding();
            binding.setAgentUserId(user.getId());
            binding.setCreateTime(LocalDateTime.now());
        }
        binding.setHmdpToken(token);
        if (hmdpUserId != null) {
            binding.setHmdpUserId(hmdpUserId);
        }
        binding.setBindStatus(1);
        binding.setUpdateTime(LocalDateTime.now());

        if (binding.getId() == null) {
            userAccountBindingMapper.insert(binding);
        } else {
            userAccountBindingMapper.updateById(binding);
        }
        return Result.ok("hmdp \u7ed1\u5b9a\u6210\u529f", binding);
    }

    @Override
    public Result bindSkyTakeOut(BindSkyTakeOutLoginRequest request) {
        User user = UserHolder.getUser();
        if (user == null) {
            return Result.error("\u7528\u6237\u672a\u767b\u5f55");
        }
        if (request == null || !hasText(request.getCode())) {
            return Result.error(400, "code \u4e0d\u80fd\u4e3a\u7a7a");
        }

        Map<String, Object> parsed;
        try {
            parsed = apiCilent.bindSkyTakeOut(request.getCode());
        } catch (Exception e) {
            return Result.error("sky_take_out \u7ed1\u5b9a\u5931\u8d25: " + e.getMessage());
        }

        String skyToken = toText(parsed.get("token"));
        Long skyUserId = parsed.get("userId") instanceof Number
                ? ((Number) parsed.get("userId")).longValue()
                : null;
        if (!hasText(skyToken)) {
            String message = toText(parsed.get("message"));
            log.warn("sky_take_out login missing token, parsed={}", parsed);
            if (hasText(message)) {
                return Result.error("sky_take_out \u767b\u5f55\u672a\u8fd4\u56de token\uff0c\u63a5\u53e3\u6d88\u606f: " + message);
            }
            return Result.error("sky_take_out \u767b\u5f55\u672a\u8fd4\u56de token\uff0c\u8bf7\u68c0\u67e5\u5916\u90e8\u63a5\u53e3 body/header");
        }

        QueryWrapper<UserAccountBinding> wrapper = new QueryWrapper<>();
        wrapper.eq("agent_user_id", user.getId());
        UserAccountBinding binding = userAccountBindingMapper.selectOne(wrapper);
        if (binding == null) {
            binding = new UserAccountBinding();
            binding.setAgentUserId(user.getId());
            binding.setCreateTime(LocalDateTime.now());
        }
        binding.setSkyTakeOutToken(skyToken);
        if (skyUserId != null) {
            binding.setSkyTakeOutUserId(skyUserId);
        }
        binding.setBindStatus(1);
        binding.setUpdateTime(LocalDateTime.now());

        if (binding.getId() == null) {
            userAccountBindingMapper.insert(binding);
        } else {
            userAccountBindingMapper.updateById(binding);
        }
        return Result.ok("sky_take_out \u7ed1\u5b9a\u6210\u529f", binding);
    }

    @Override
    public Result getExternalBinding() {
        User user = UserHolder.getUser();
        if (user == null) {
            return Result.error("\u7528\u6237\u672a\u767b\u5f55");
        }
        QueryWrapper<UserAccountBinding> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("agent_user_id", user.getId());
        UserAccountBinding binding = userAccountBindingMapper.selectOne(queryWrapper);
        if (binding == null) {
            return Result.error(404, "\u5f53\u524d\u7528\u6237\u672a\u7ed1\u5b9a\u5916\u90e8\u8d26\u53f7");
        }
        return Result.ok(buildBindingView(binding));
    }

    private Map<String, Object> buildBindingView(UserAccountBinding binding) {
        Map<String, Object> view = new LinkedHashMap<>();
        boolean hmdpBound = binding.getHmdpUserId() != null || hasText(binding.getHmdpToken());
        boolean skyTakeOutBound = binding.getSkyTakeOutUserId() != null || hasText(binding.getSkyTakeOutToken());
        Map<String, String> hmdpProfile = loadHmdpProfile(binding.getHmdpUserId());
        Map<String, String> skyTakeOutProfile = loadSkyTakeOutProfile(binding.getSkyTakeOutUserId());

        view.put("id", binding.getId());
        view.put("agent_user_id", binding.getAgentUserId());
        view.put("hmdp_user_id", binding.getHmdpUserId());
        view.put("sky_take_out_user_id", binding.getSkyTakeOutUserId());
        view.put("hmdp_token", binding.getHmdpToken());
        view.put("sky_take_out_token", binding.getSkyTakeOutToken());
        view.put("bind_status", binding.getBindStatus());
        view.put("create_time", binding.getCreateTime());
        view.put("update_time", binding.getUpdateTime());

        view.put("hmdp_bound", hmdpBound);
        view.put("hmdp_username", hmdpProfile.get("username"));
        view.put("hmdp_phone", hmdpProfile.get("phone"));
        view.put("hmdp_display_name", firstNonBlank(hmdpProfile.get("username"), hmdpProfile.get("phone"), hmdpBound ? "\u5df2\u7ed1\u5b9a" : null));

        view.put("sky_take_out_bound", skyTakeOutBound);
        view.put("sky_take_out_username", skyTakeOutProfile.get("username"));
        view.put("sky_take_out_phone", skyTakeOutProfile.get("phone"));
        view.put(
                "sky_take_out_display_name",
                firstNonBlank(skyTakeOutProfile.get("username"), skyTakeOutProfile.get("phone"), skyTakeOutBound ? "\u5df2\u7ed1\u5b9a" : null)
        );
        return view;
    }

    private Map<String, String> loadHmdpProfile(Long userId) {
        return loadExternalProfile(
                "hmdp",
                "SELECT nick_name AS username, phone FROM hmdp.tb_user WHERE id = ? LIMIT 1",
                userId
        );
    }

    private Map<String, String> loadSkyTakeOutProfile(Long userId) {
        Map<String, String> profile = loadExternalProfile(
                "sky_take_out",
                "SELECT name AS username, phone FROM sky_take_out.user WHERE id = ? LIMIT 1",
                userId
        );
        if (!profile.isEmpty()) {
            return profile;
        }
        return loadExternalProfile(
                "sky_take_out",
                "SELECT openid AS username, phone FROM sky_take_out.user WHERE id = ? LIMIT 1",
                userId
        );
    }

    private Map<String, String> loadExternalProfile(String source, String sql, Long userId) {
        if (userId == null) {
            return Collections.emptyMap();
        }
        try {
            List<Map<String, Object>> rows = jdbcTemplate.queryForList(sql, userId);
            if (rows.isEmpty()) {
                return Collections.emptyMap();
            }
            Map<String, Object> row = rows.get(0);
            Map<String, String> result = new LinkedHashMap<>();
            result.put("username", toText(row.get("username")));
            result.put("phone", toText(row.get("phone")));
            return result;
        } catch (Exception e) {
            log.debug("load {} profile failed for userId={}: {}", source, userId, e.getMessage());
            return Collections.emptyMap();
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
}
