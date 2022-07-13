#pragma once

#include <iostream>
#include <filesystem>
#include <fstream>
#include <set>

#include "paths.h"

#define SET_CONTAINS(set,value) ((set).find(value) != (set).end())

#define ALL_DEPTH_FOLDERS   -1  //accept all kinds of subfolders in the working data folder
//depth 0 is WORKING_DATA_FOLDER
#define DEPTH_1_CAD         1   //accept only CAD input folders
#define DEPTH_2_TETRA_MESH  2   //accept only tetra mesh input folders
#define DEPTH_3_LABELING    3   //accept only labeling input folders
#define DEPTH_4_HEX_MESH    4   //accept only hex mesh input folders

// #define DEBUG_EXPAND_COLLECTION

// INPUTS
//   'collection' is the path to a .txt collection file (case multiple entries), or to a folder (case unique entry)
//   'working_data_folder' is the path to the working data folder
//   'requested_depth' is the depth (relative to 'working_data_folder') requested by the application for its inputs (ex: naive_labeling -> depth of 2). -1 = all depths accepted
// OUTPUTS
//   'entries' will list all the folders that 'collection' contains
//   returne value : 1 if an error occured, else 0
// INTERNALS (for recursion)
//   'subcollections' ensure there is no cyclic inclusion
bool expand_collection(const std::filesystem::path& collection_, const std::filesystem::path& working_data_folder, int requested_depth, std::set<std::filesystem::path>& entries, std::set<std::filesystem::path>& subcollections) {

    auto collection = normalized_trimed(collection_);
    //working_data_folder must be normalized & trimed before

    int depth = get_depth_relative(working_data_folder,collection);

    if(depth==-1) {
        std::cerr << "Error : " << collection.string() << " is not a subfolder of " << working_data_folder.string() << "," << std::endl;
        std::cerr << "the working data folder defined in path.json" << std::endl;
        return 1;
    }

    if(!std::filesystem::exists(collection)) {
        std::cerr << "Error : " << collection.string() << " doesn't exist" << std::endl;
        return 1;
    }

    if(std::filesystem::is_directory(collection)) {
        //when expand_collection() is called recursively, 'collection' is ensured to be a .txt file
        //but the top level call of expand_collection() could recieve a folder,
        //which means the user only chose one entry
        if( (requested_depth!=ALL_DEPTH_FOLDERS) && (depth != requested_depth) ) {
            std::cerr << "Error : the depth (" << depth << ") of " << collection.string() << " is invalid." << std::endl;
            std::cerr << "This application requires input folders of depth " << requested_depth << " relative to " << working_data_folder.string() << "." << std::endl;
            return 1;
        }
        else {
#ifdef DEBUG_EXPAND_COLLECTION
            std::cout << "Found " << collection.string() << ", relative depth " << depth << std::endl;
#endif
            entries.emplace(normalized_trimed(collection));
        }
    }
    else if(collection.extension()!=".txt") {
        std::cerr << "Error : " << collection.string() << " is neither a .txt file nor a folder" << std::endl;
        return 1;
    }
    
    std::ifstream input_file(collection);
    std::string line;
    std::filesystem::path new_entry;
    int new_entry_depth;
    if (!input_file.is_open()) {
        std::cerr << "Error : could not open " + collection.string() << std::endl;
        return 0;
    }
    
    while (std::getline(input_file,line)) { //read line by line

        if(line.empty() || line[0] == '#') { //ignore empty lines and the ones starting with '#'
            continue;
        }

        new_entry = collection.parent_path() / line;
        new_entry = normalized_trimed(new_entry);

        //a collection can only contains directories (the entries) or .txt files (subcollections)

        if(std::filesystem::is_directory(new_entry)) {
            //check if this new entry is of same depth as the others
            new_entry_depth = get_depth_relative(working_data_folder,new_entry);
            if( (requested_depth!=ALL_DEPTH_FOLDERS) && (new_entry_depth != requested_depth) ) {//if the depth of this entry is invalid
                std::cerr << "Error : the depth (" << new_entry_depth << ") of " << line << " (in " << collection.string() << ") is invalid." << std::endl;
                std::cerr << "This application requires input folders of depth " << requested_depth << " relative to " << working_data_folder.string() << "." << std::endl;
                return 1;
            }
#ifdef DEBUG_EXPAND_COLLECTION
            std::cout << "Found " << new_entry.string() << ", relative depth " << new_entry_depth << std::endl;
#endif
            entries.emplace(new_entry);
        }
        else if(std::filesystem::is_regular_file(new_entry)) {
            if(new_entry.extension()==".txt") {
                //to avoid cyclic inclusion of collections, i.e. a.txt containing b.txt containing a.txt,
                //store the subcollections found in a set, and ignore already-opened collections
                if(SET_CONTAINS(subcollections,new_entry)) {
                    std::cout << "Info : " << collection.string() << " has already been opened and will be skipped" << std::endl;
                    continue;//jump to next line
                }
                subcollections.emplace(collection);
                if(expand_collection(new_entry,working_data_folder,requested_depth,entries,subcollections)) {
                    return 1;
                }
                //else the recursive call of expand_collection() didn't encountered any issue -> continue reading
            }
            else {
                std::cerr << "Error : " << line << " (in " << collection.string() << ") is not a .txt file" << std::endl;
                return 1;
            }
        }
        else {
            std::cerr << "Error : " << line << " (in " << collection.string() << ") isn't a valid file" << std::endl;
            return 1;
        }
    }

    return 0;
}

class OutputCollection {
public:
    OutputCollection(std::filesystem::path path, const std::string& header) : _path(path), _nb_entries(0), _header(header) {
        _ofs.open(path,std::ios_base::app);//always append to existing file
        if(!_ofs.is_open()) {
            std::cerr << "Error : Failed to open " << path.string() << std::endl;
            exit(1);
        }
    }

    ~OutputCollection() {
        _ofs.close();
    }

    void new_entry(std::filesystem::path entry) {
        _nb_entries++;
        if(_nb_entries==1) {
            print_header();
        }
        _ofs << std::filesystem::relative(entry,_path.parent_path()).string() << std::endl;
    }

    void new_comments(std::string str) {
        _ofs << "# " << str << std::endl;
    }

    void new_line() {
        _ofs << std::endl;
    }

    void print_header() {
        _ofs << std::endl;
        _ofs << _header << std::endl;
    }

private:
    std::ofstream _ofs;
    std::filesystem::path _path;
    unsigned int _nb_entries;
    const std::string& _header;
};

class OutputCollections {

public:
    OutputCollections(std::string base_filename, const PathList& path_list, bool disabled) : _header("") {
        path_list.require(WORKING_DATA_FOLDER);
        
        if(disabled) {
            success_cases = new OutputCollection("/dev/null",_header);
            error_cases = new OutputCollection("/dev/null",_header);
        }
        else {
            std::filesystem::path success_cases_path = path_list[WORKING_DATA_FOLDER] / (base_filename+".txt");
            std::filesystem::path error_cases_path = path_list[WORKING_DATA_FOLDER] / (base_filename+"_errors.txt");
            success_cases = new OutputCollection(success_cases_path,_header);
            error_cases = new OutputCollection(error_cases_path,_header);
            std::cout << "Output collection : " << success_cases_path.string() << std::endl;
            std::cout << "Output collection : " << error_cases_path.string() << std::endl;
        }
    }

    ~OutputCollections() {
        delete success_cases;
        delete error_cases;
    }

    void set_header(std::string executable_name, std::string datetime, std::string comments) {
        _header = "# Generated by " + executable_name + "\n# " + datetime;
        if(!comments.empty()) {
            _header += "\n# " + comments;
        }
    }

    OutputCollection *success_cases, *error_cases;

private:
    std::string _header;
};