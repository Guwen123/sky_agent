package com.agent.controller;

import com.agent.entity.Result;
import com.agent.utils.CaptchaUtil;
import com.agent.utils.JwtUtil;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class LoginController {

    @Resource
    private CaptchaUtil captchaUtil;

    @PostMapping("/login")
    public Result login(@RequestBody Map<String, String> loginData) {
        String username = loginData.get("username");
        String password = loginData.get("password");
        String captcha = loginData.get("captcha");
        
        // 验证验证码
        if (!captchaUtil.validateCaptcha(username, captcha)) {
            return Result.error(400, "验证码错误或已过期");
        }
        
        // 这里应该进行用户验证，暂时模拟验证成功
        if ("admin".equals(username) && "123456".equals(password)) {
            // 生成JWT token
            Map<String, Object> claims = new HashMap<>();
            claims.put("username", username);
            String token = JwtUtil.generateToken(username, claims);
            
            // 删除验证码
            captchaUtil.removeCaptcha(username);
            
            Map<String, Object> data = new HashMap<>();
            data.put("token", token);
            return Result.ok("登录成功", data);
        } else {
            return Result.error(401, "用户名或密码错误");
        }
    }

    @PostMapping("/captcha")
    public Result getCaptcha(@RequestBody Map<String, String> requestData) {
        String username = requestData.get("username");
        if (username == null || username.isEmpty()) {
            return Result.error(400, "用户名不能为空");
        }
        
        // 生成验证码
        String captcha = captchaUtil.generateCaptcha(username);
        
        Map<String, Object> data = new HashMap<>();
        data.put("captcha", captcha); // 实际生产环境中应该通过邮件或短信发送验证码
        return Result.ok("验证码生成成功", data);
    }
}