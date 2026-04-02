package com.agent.service;

import com.agent.entity.Result;
import com.agent.entity.User;
import com.agent.entity.loginData;

public interface loginService {
    Result login(loginData user);

    Result getLoginCaptcha(String username);

    Result getRegisterCaptcha(String username);

    Result register(loginData user);
}
