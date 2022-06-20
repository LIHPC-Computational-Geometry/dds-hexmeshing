#pragma once

#include <stdlib.h>
#include <iostream>
#include <filesystem>
#include <fstream>
#include <string>
#include <nlohmann/json.hpp>

class paths {

public:
    paths() {
        std::ifstream i("../paths.json");
        if (i.good()) {
            i >> _j;
            _shared_data = to_canonical_path(_j.value<std::string>("/shared_data"_json_pointer,""));
        }
        else
            std::cerr << "Error : paths.json doesn't exist" << std::endl;
        i.close();
    };

    std::filesystem::path shared_data() {
        return _shared_data;
    };

private:
    nlohmann::json _j;
    std::filesystem::path _shared_data;

    std::filesystem::path to_canonical_path(std::string path_as_str) {
        if(path_as_str.size()>=1 && path_as_str[0]=='~') {
            //replace "~" with the value of $HOME
            path_as_str = getenv("HOME") + path_as_str.substr(1);
        }
        return std::filesystem::weakly_canonical(path_as_str);//do not check if the path exist
    };
};