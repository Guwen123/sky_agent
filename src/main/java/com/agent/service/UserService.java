package com.agent.service;

import com.agent.entity.Result;

public interface UserService {
    public Result detail();

    public Result logout();
    
    public Result talk(String question);
}
