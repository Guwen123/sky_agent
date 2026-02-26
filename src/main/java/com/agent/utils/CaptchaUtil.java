package com.agent.utils;

import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.util.Random;
import java.util.concurrent.TimeUnit;

@Component
public class CaptchaUtil {

    @Resource
    private RedisTemplate<String, String> redisTemplate;

    // 生成6位数字验证码
    public String generateCaptcha(String username) {
        Random random = new Random();
        StringBuilder captcha = new StringBuilder();
        for (int i = 0; i < 6; i++) {
            captcha.append(random.nextInt(10));
        }
        // 将验证码存储到Redis，有效期5分钟
        redisTemplate.opsForValue().set("captcha:" + username, captcha.toString(), 5, TimeUnit.MINUTES);
        return captcha.toString();
    }

    // 验证验证码
    public boolean validateCaptcha(String username, String captcha) {
        String storedCaptcha = redisTemplate.opsForValue().get("captcha:" + username);
        return captcha != null && captcha.equals(storedCaptcha);
    }

    // 删除验证码
    public void removeCaptcha(String username) {
        redisTemplate.delete("captcha:" + username);
    }
}