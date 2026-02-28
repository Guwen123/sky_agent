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
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

import javax.annotation.Resource;
import java.util.HashMap;
import java.util.Map;

@Service
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

        // 验证验证码
        if (!captchaUtil.validateCaptcha(username, captcha)) {
            return Result.error(400, "验证码错误或已过期");
        }

        // 从数据库根据用户名查找用户
        QueryWrapper<User> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("username", username);
        User dbUser = userMapper.selectOne(queryWrapper);

        // 检查用户是否存在
        if (dbUser == null) {
            return Result.error(401, "用户名不存在");
        }

        // 检查密码是否正确
        if (!dbUser.getPassword().equals(password)) {
            return Result.error(401, "密码错误");
        }

        // 检查用户状态
        if (dbUser.getStatus() == 0) {
            return Result.error(403, "账号已被禁用");
        }

        // 登录成功，生成JWT token
        Map<String, Object> claims = new HashMap<>();
        claims.put("username", username);
        claims.put("userId", dbUser.getId());
        String token = JwtUtil.generateToken(username, claims);

        // 删除验证码
        captchaUtil.removeCaptcha(username);

        return Result.ok("登录成功", token);
    }

    @Override
    public Result getCaptcha(String username) {
        if (username == null || username.isEmpty()) {
            return Result.error(400, "用户名不能为空");
        }

        // 生成验证码
        String captcha = captchaUtil.generateCaptcha(username);

        Map<String, Object> data = new HashMap<>();
        data.put("captcha", captcha); // 实际生产环境中应该通过邮件或短信发送验证码
        return Result.ok("验证码生成成功", data);
    }

    @Override
    public Result register(User user) {
        String username = user.getUsername();
        String password = user.getPassword();

        // 参数校验
        if (username == null || username.isEmpty()) {
            return Result.error(400, "用户名不能为空");
        }
        if (password == null || password.isEmpty()) {
            return Result.error(400, "密码不能为空");
        }

        // 检查用户名是否已存在
        QueryWrapper<User> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("username", username);
        User existUser = userMapper.selectOne(queryWrapper);
        if (existUser != null) {
            return Result.error(400, "用户名已存在");
        }

        // 保存用户信息
        // 加密密码
        MessageDigest md;
        try {
            md = MessageDigest.getInstance("MD5");
        } catch (NoSuchAlgorithmException e) {
            return Result.error(500, "MD5算法不存在");
        }
        byte[] encryptedPassword = md.digest(password.getBytes());
        user.setPassword(new String(encryptedPassword));
        user.setStatus(1);
        user.setCreateTime(java.time.LocalDateTime.now());
        user.setUpdateTime(java.time.LocalDateTime.now());

        int result = userMapper.insert(user);
        if (result > 0) {
            return Result.ok("注册成功");
        } else {
            return Result.error(500, "注册失败");
        }
    }
}