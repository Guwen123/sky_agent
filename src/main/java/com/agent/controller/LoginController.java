package com.agent.controller;

import com.agent.entity.Result;
import com.agent.service.loginService;
import com.agent.entity.loginData;
import com.agent.entity.User;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestParam;

import javax.annotation.Resource;

@RestController
@RequestMapping("/api")
public class LoginController {

    @Resource
    private loginService loginService;

    @PostMapping("/login")
    public Result login(@RequestBody loginData user) {
        return loginService.login(user);
    }

    @GetMapping("/captcha")
    public Result getCaptcha(@RequestParam String username) {
        return loginService.getCaptcha(username);
    }

    @PostMapping("/register")
    public Result register(@RequestBody User user) {
        return loginService.register(user);
    }
}