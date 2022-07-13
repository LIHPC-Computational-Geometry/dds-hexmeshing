#pragma once

#include <iostream>
#include <algorithm>
#include <cctype>
#include <string>

enum special_case_policy {
    ask = 0,//ask [yes/no/always_yes/always_no] every time
    always_yes,
    always_no
};
typedef enum special_case_policy special_case_policy;

std::string to_string(special_case_policy policy) {
    switch(policy) {
        case ask:
            return "ask";
        case always_yes:
            return "always_yes";
        case always_no:
            return "always_no";
        default:
            return "BAD_VALUE";
    }
}

//return value: true=yes, false=no
bool ask_for_confirmation(std::string question, special_case_policy& policy) {

    //check the policy
    if(policy == always_yes) {
        return true;
    }
    else if(policy == always_no) {
        return false;
    }
    else {

        //ask the question
        std::string input;
        do {
            std::cout << question << " [y/n/always_yes/always_no] " << std::flush;
            std::cin >> input;
            //to lowercase
            std::transform(input.begin(), input.end(), input.begin(),[](unsigned char c){ return std::tolower(c); });
        }
        while (
            (input != "y") &&
            (input != "n") &&
            (input != "always_yes") &&
            (input != "always_no")
        );

        //eventually update the policy
        if(input == "always_yes") {
            policy = always_yes;
        }
        else if(input == "always_no") {
            policy = always_no;
        }

        //return user choice
        return ((input == "y") || (input == "always_yes"));
    }
}

//version without special_case_policy (only yes/no)
//return value: true=yes, false=no
bool ask_for_confirmation(std::string question) {
    std::string input;
    do {
        std::cout << question << " [y/n] " << std::flush;
        std::cin >> input;
        //to lowercase
        std::transform(input.begin(), input.end(), input.begin(),[](unsigned char c){ return std::tolower(c); });
    }
    while (
        (input != "y") &&
        (input != "n")
    );

    //return user choice
    return (input == "y");
}