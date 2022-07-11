#pragma once

#include <iostream>
#include <filesystem>
#include <fstream>
#include <set>

#include "paths.h"

#define SET_CONTAINS(set,value) ((set).find(value) != (set).end())

// for the constructor of OutputCollection
#define NOTIFY          true
#define DO_NOT_NOTIFY   false

//from https://stackoverflow.com/a/60532070
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
    return m.first == b.end();
}

//count the number of folders +1 between a file/folder and the root
int get_depth(std::filesystem::path p) {
    if(p == p.parent_path()) {
        //we reached the root path
        return 0;
    }
    else if (p.filename()=="")
    {
        //even though the parent path of /var/tmp/ is /var/tmp, consider they have the same depth
        return get_depth(p.parent_path());
    }
    else {
        return get_depth(p.parent_path())+1;
    }
}

//'collection' is the path to a .txt collection file (case multiple entries), or to a folder (case unique entry)
//'entries' will list all the folders that 'collection' contains
//'subcollections' ensure there is no cyclic inclusion
//'depth' ensure all the folders have the same depth (distance to root)
//return 1 if an error occured
bool expand_collection(const std::filesystem::path& collection, const std::filesystem::path& working_data_folder, std::set<std::filesystem::path>& entries, std::set<std::filesystem::path>& subcollections, int depth=-1) {

    if(!is_subpath_of(working_data_folder,collection)) {
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
        entries.emplace(normalized_trimed(collection));
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
            new_entry_depth = get_depth(new_entry);
            if(depth == -1) { //if depth is undefined (case of the first entry found)
                depth = new_entry_depth;//store the depth ("distance" to root)
            }
            else if(new_entry_depth != depth) {//if the depth of this entry is different
                std::cerr << "Error : the depth of " << line << " (in " << collection.string() << ") is different from the previous entries" << std::endl;
                return 1;
            }
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
                if(expand_collection(new_entry,working_data_folder,entries,subcollections,depth)) {
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