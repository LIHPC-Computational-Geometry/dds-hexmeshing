#pragma once

#include <stdlib.h>
#include <iostream>
#include <filesystem>
#include <fstream>
#include <string>
#include <map>
#include <initializer_list>
#include <nlohmann/json.hpp>

#include "parameters.h"

// ~~~~~~~~~~ from https://stackoverflow.com/a/60532070 ~~~~~~~~~~~~~~~~~

std::filesystem::path normalized_trimed(const std::filesystem::path& p)
{
    auto r = std::filesystem::weakly_canonical(p).lexically_normal();
    if (r.has_filename()) return r;
    return r.parent_path();
}

bool is_subpath_of(const std::filesystem::path& base, const std::filesystem::path& sub)
{
    auto b = normalized_trimed(base);
    auto s = normalized_trimed(sub).parent_path();
    auto m = std::mismatch(b.begin(), b.end(), 
                           s.begin(), s.end());
    bool result = (m.first == b.end());
    return result;
}

// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


//count the number of folders +1 between a file/folder and the root
int get_depth(std::filesystem::path p) {
    p = normalized_trimed(p);
    if(p == p.parent_path()) {
        //we reached the root path
        return 0;
    }
    else {
        return get_depth(p.parent_path())+1;
    }
}

//warning : base & sub must be normalized and trimed
int get_depth_relative(std::filesystem::path base, std::filesystem::path sub) {
    
    if(sub == base) {
        return 0;
    }
    else if(sub == sub.parent_path()) { //if sub is the root
        return -1;//sub is not relative to base
    }
    else {
        int sub_depth = get_depth_relative(base,sub.parent_path());//get relative depth of parent path
        if(sub_depth == -1) {
            return -1;//propagate -1 return code
        }
        else {
            return sub_depth+1;//relative depth is one more than the one of the parent path
        }
    }
}

std::filesystem::path to_canonical_path(std::string path_as_str) {
    //case of a path relative to the home folder
    if(path_as_str.size()>=1 && path_as_str[0]=='~') {
        //replace "~" with the value of $HOME
        path_as_str = getenv("HOME") + path_as_str.substr(1);
    }
    //case of a path relative to paths.json
    else if(path_as_str.size()>=2 && path_as_str[0]=='.' && path_as_str[1]=='.') {
        path_as_str = "../" + path_as_str;//from the build folder, paths.json is one level higher
    }
    //else its an absolute path, no modification needed
    return normalized_trimed(path_as_str);
};

//if 'entry_name' is an entry of 'json' and is not empty, add it to 'string2path'
inline void try_to_insert(const nlohmann::json& json, std::map<std::string,std::filesystem::path>& string2path, std::string entry_name) {
    try {
        std::filesystem::path tmp_path = to_canonical_path(json.at( nlohmann::json::json_pointer("/"+entry_name) ));
        if(!tmp_path.empty()) {
            string2path[entry_name] = tmp_path;
        }
    }
    catch (nlohmann::json::out_of_range) { /* if 'entry_name' does not exist in 'json', no entry added in 'string2path' */ }
};

class PathList {

public:
    PathList() {
        std::ifstream i("../paths.json");
        if (i.good()) {
            i >> _j;
            try_to_insert(_j,_string2path,WORKING_DATA_FOLDER);
            try_to_insert(_j,_string2path,SALOME);
            try_to_insert(_j,_string2path,GENOMESH);
            try_to_insert(_j,_string2path,EVOCUBE_TWEAKS);
            try_to_insert(_j,_string2path,ROBUST_POLYCUBE);
        }
        else
            std::cerr << "Error : paths.json doesn't exist" << std::endl;
        i.close();
    };

    void dump() {
        for(auto it = _string2path.begin(); it != _string2path.end(); ++it) {
            std::cout << "_string2path[\"" << it->first << "\"]=" << (it->second).string() << std::endl;
        }
    }

    std::filesystem::path operator[](std::string entry) const {
        return _string2path.at(entry);
    }

    void require(std::string entry, bool must_be_valid_path = true) const {
        try {
            if(must_be_valid_path) {
                // try to access this entry + check if the path exist
                if(!std::filesystem::exists(_string2path.at(entry))) {
                    std::cerr << "Error : '" << entry << "' is required in paths.json, but the given path is invalid" << std::endl;
                    exit(1);
                }
            }
            else {
                // try to access this entry
                _string2path.at(entry);
            }
        }
        catch (std::out_of_range) {
            std::cerr << "Error : '" << entry << "' is required in paths.json" << std::endl;
            exit(1);
        }
        return;
    }

private:
    nlohmann::json _j;
    std::map<std::string,std::filesystem::path> _string2path;
};

int existing_files_among(std::initializer_list<std::filesystem::path> file_list, const std::filesystem::path& working_data_folder, bool verbose=false) {
    int existing_files_counter = 0;
    for(auto* file = file_list.begin(); file != file_list.end(); ++file) {
        if(std::filesystem::exists(*file)) {
            existing_files_counter++;
            if(verbose) {
                if(existing_files_counter==1) { std::cout << "Warning" << std::endl; }//case 1st printing
                std::cout << "\t" << std::filesystem::relative(*file,working_data_folder).string() << " already exists" << std::endl;
            }
        }
    }
    return existing_files_counter;
}

int missing_files_among(std::initializer_list<std::filesystem::path> file_list, const std::filesystem::path& working_data_folder, bool verbose=false) {
    int missing_files_counter = 0;
    for(auto* file = file_list.begin(); file != file_list.end(); ++file) {
        if(!std::filesystem::exists(*file)) {
            missing_files_counter++;
            if(verbose) {
                if(missing_files_counter==1) { std::cout << "Warning" << std::endl; }//case 1st printing
                std::cout << "\t" << std::filesystem::relative(*file,working_data_folder).string() << " is missing" << std::endl;
            }
        }
    }
    return missing_files_counter;
}