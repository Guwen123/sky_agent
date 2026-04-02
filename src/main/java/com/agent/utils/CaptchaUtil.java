package com.agent.utils;

import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.util.Random;
import java.util.concurrent.TimeUnit;

@Component
public class CaptchaUtil {

    private static final String LOGIN_SCENE = "login";
    private static final String REGISTER_SCENE = "register";

    @Resource
    private RedisTemplate<String, String> redisTemplate;

    public String generateLoginCaptcha(String username) {
        return generateCaptcha(username, LOGIN_SCENE);
    }

    public String generateRegisterCaptcha(String username) {
        return generateCaptcha(username, REGISTER_SCENE);
    }

    public boolean validateLoginCaptcha(String username, String captcha) {
        return validateCaptcha(username, captcha, LOGIN_SCENE);
    }

    public boolean validateRegisterCaptcha(String username, String captcha) {
        return validateCaptcha(username, captcha, REGISTER_SCENE);
    }

    public void removeLoginCaptcha(String username) {
        removeCaptcha(username, LOGIN_SCENE);
    }

    public void removeRegisterCaptcha(String username) {
        removeCaptcha(username, REGISTER_SCENE);
    }

    private String generateCaptcha(String username, String scene) {
        Random random = new Random();
        StringBuilder captcha = new StringBuilder();
        for (int i = 0; i < 6; i++) {
            captcha.append(random.nextInt(10));
        }
        redisTemplate.opsForValue().set(buildKey(username, scene), captcha.toString(), 5, TimeUnit.MINUTES);
        return captcha.toString();
    }

    private boolean validateCaptcha(String username, String captcha, String scene) {
        String storedCaptcha = redisTemplate.opsForValue().get(buildKey(username, scene));
        return captcha != null && captcha.equals(storedCaptcha);
    }

    private void removeCaptcha(String username, String scene) {
        redisTemplate.delete(buildKey(username, scene));
    }

    private String buildKey(String username, String scene) {
        return "captcha:" + scene + ":" + username;
    }
}
