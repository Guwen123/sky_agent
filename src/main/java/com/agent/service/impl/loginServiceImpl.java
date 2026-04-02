package com.agent.service.impl;

import com.agent.entity.Result;
import com.agent.entity.User;
import com.agent.entity.loginData;
import com.agent.mapper.UserMapper;
import com.agent.service.loginService;
import com.agent.utils.CaptchaUtil;
import com.agent.utils.JwtUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

import lombok.extern.slf4j.Slf4j;

@Service
@Slf4j
public class loginServiceImpl implements loginService {

    @Resource
    private UserMapper userMapper;

    @Resource
    private CaptchaUtil captchaUtil;

    @Override
    public Result login(loginData user) {
        String username = user.getUsername();
        String password = user.getPassword();
        String captcha = user.getCaptcha();

        if (!captchaUtil.validateLoginCaptcha(username, captcha)) {
            return Result.error(400, "验证码错误或已过期");
        }

        QueryWrapper<User> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("username", username);
        User dbUser = userMapper.selectOne(queryWrapper);

        if (dbUser == null) {
            return Result.error(401, "用户名不存在");
        }

        String encryptedInput;
        try {
            encryptedInput = md5Hex(password);
        } catch (NoSuchAlgorithmException e) {
            return Result.error(500, "MD5算法不可用");
        }

        if (!encryptedInput.equals(dbUser.getPassword())) {
            return Result.error(401, "密码错误");
        }

        if (dbUser.getStatus() == 0) {
            return Result.error(403, "账号已被禁用");
        }

        Map<String, Object> claims = new HashMap<>();
        claims.put("username", username);
        claims.put("userId", dbUser.getId());
        String token = JwtUtil.generateToken(username, claims);

        captchaUtil.removeLoginCaptcha(username);
        return Result.ok("登录成功", token);
    }

    @Override
    public Result getLoginCaptcha(String username) {
        if (username == null || username.isEmpty()) {
            return Result.error(400, "用户名不能为空");
        }
        String captcha = captchaUtil.generateLoginCaptcha(username);
        log.info("login captcha username={}, code={}", username, captcha);
        Map<String, Object> data = new HashMap<>();
        data.put("captcha", captcha);
        return Result.ok("登录验证码生成成功", data);
    }

    @Override
    public Result getRegisterCaptcha(String username) {
        if (username == null || username.isEmpty()) {
            return Result.error(400, "用户名不能为空");
        }
        String captcha = captchaUtil.generateRegisterCaptcha(username);
        log.info("register captcha username={}, code={}", username, captcha);
        Map<String, Object> data = new HashMap<>();
        data.put("captcha", captcha);
        return Result.ok("注册验证码生成成功", data);
    }

    @Override
    public Result register(loginData user) {
        String username = user.getUsername();
        String password = user.getPassword();
        String captcha = user.getCaptcha();

        if (username == null || username.isEmpty()) {
            return Result.error(400, "用户名不能为空");
        }
        if (password == null || password.isEmpty()) {
            return Result.error(400, "密码不能为空");
        }
        if (captcha == null || captcha.isEmpty()) {
            return Result.error(400, "验证码不能为空");
        }

        if (!captchaUtil.validateRegisterCaptcha(username, captcha)) {
            return Result.error(400, "验证码错误或已过期");
        }

        QueryWrapper<User> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("username", username);
        User existUser = userMapper.selectOne(queryWrapper);
        if (existUser != null) {
            return Result.error(400, "用户名已存在");
        }

        String encryptedPassword;
        try {
            encryptedPassword = md5Hex(password);
        } catch (NoSuchAlgorithmException e) {
            return Result.error(500, "MD5算法不可用");
        }

        User newUser = User.builder()
                .username(username)
                .password(encryptedPassword)
                .status(1)
                .createTime(LocalDateTime.now())
                .updateTime(LocalDateTime.now())
                .build();

        int result = userMapper.insert(newUser);
        if (result > 0) {
            captchaUtil.removeRegisterCaptcha(username);
            return Result.ok("注册成功");
        }
        return Result.error(500, "注册失败");
    }

    private String md5Hex(String input) throws NoSuchAlgorithmException {
        MessageDigest md = MessageDigest.getInstance("MD5");
        byte[] digest = md.digest(input.getBytes(StandardCharsets.UTF_8));
        StringBuilder sb = new StringBuilder(digest.length * 2);
        for (byte b : digest) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
