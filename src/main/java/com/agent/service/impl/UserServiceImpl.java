package com.agent.service.impl;

import com.agent.entity.Result;
import com.agent.mapper.UserMapper;
import com.agent.entity.User;
import com.agent.service.UserService;
import org.springframework.stereotype.Service;

import com.agent.utils.JwtUtil;
import com.agent.utils.UserHolder;

import javax.annotation.Resource;

@Service
public class UserServiceImpl implements UserService {
    @Resource
    private UserMapper userMapper;

    @Override
    public Result detail() {
        // 从ThreadLocal获取当前登录用户
        User user = UserHolder.getUser();
        if (user == null) {
            return Result.error("用户未登录");
        }
        return Result.ok(user);
    }
}
