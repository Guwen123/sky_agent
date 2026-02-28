package com.agent.service;

import com.agent.entity.Result;
import com.agent.entity.User;
import com.agent.entity.loginData;

public interface loginService {
    Result login(loginData user);

    Result getCaptcha(String username);

    Result register(User user);
}