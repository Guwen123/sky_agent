package com.agent.controller;

import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestMapping;

import javax.annotation.Resource;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.GetMapping;

import com.agent.entity.Result;
import com.agent.service.UserService;
import org.springframework.web.bind.annotation.RequestParam;

@RestController
@RequestMapping("/user")
public class UserController {
    @Resource
    private UserService userService;

    @PostMapping("/detail")
    public Result detail() {
        return userService.detail();
    }

    @GetMapping("/logout")
    public Result logout() {
        return userService.logout();
    }

    @GetMapping("/talk")
    public Result talk(@RequestParam String question) {
        return userService.talk(question);
    }

}
