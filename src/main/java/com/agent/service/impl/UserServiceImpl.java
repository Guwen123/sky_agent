package com.agent.service.impl;

import com.agent.entity.Result;
import com.agent.mapper.UserMapper;
import com.agent.entity.User;
import com.agent.service.UserService;
import org.springframework.stereotype.Service;

import com.agent.utils.UserHolder;
import java.time.LocalDateTime;

import javax.annotation.Resource;
import com.agent.utils.ApiCilent;

@Service
public class UserServiceImpl implements UserService {
    @Resource
    private UserMapper userMapper;
    @Resource
    private ApiCilent apiCilent;

    @Override
    public Result detail() {
        // 从ThreadLocal获取当前登录用户
        User user = UserHolder.getUser();
        if (user == null) {
            return Result.error("用户未登录");
        }
        return Result.ok(user);
    }

    @Override
    public Result logout() {
        // 从ThreadLocal移除当前登录用户
        UserHolder.removeUser();
        return Result.ok("退出成功");
    }

    @Override
    public Result talk(String question) {
        // 从ThreadLocal获取当前登录用户
        User user = UserHolder.getUser();
        String response = null;
        // 更新最后一次活跃时间
        LocalDateTime now = LocalDateTime.now();
        userMapper.updateById(User.builder()
                .id(user.getId())
                .updateTime(now)
                .build());
        // 调用Agent服务
        response = apiCilent.post(question, user.getId().toString());

        return Result.ok(response);
    }
}
