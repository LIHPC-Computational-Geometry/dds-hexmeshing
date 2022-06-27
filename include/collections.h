#pragma once

#include <iostream>
#include <filesystem>
#include <fstream>
#include <set>

#include "paths.h"

#define SET_CONTAINS(set,value) ((set).find(value) != (set).end())

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
bool expand_collection(const std::filesystem::path& collection, std::set<std::filesystem::path>& entries, std::set<std::filesystem::path>& subcollections, int depth=-1) {

    if(!std::filesystem::exists(collection)) {
        std::cerr << "Error : " << collection.string() << " doesn't exist" << std::endl;
        return 1;
    }

    if(std::filesystem::is_directory(collection)) {
        //when expand_collection() is called recursively, 'collection' is ensured to be a .txt file
        //but the top level call of expand_collection() could recieve a folder,
        //which means the user only chose one entry
        entries.emplace(collection);
        return 0;
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

        if(line[0] == '#') { //ignore lines starting with '#'
            continue;
        }

        new_entry = collection.parent_path() / line;

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
                if(expand_collection(new_entry,entries,subcollections,depth)) {
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
    OutputCollection(std::string filename, const PathList& path_list, bool remove_if_empty = true) : _remove_if_empty(remove_if_empty), _nb_entries(0) {
        path_list.require(OUTPUT_COLLECTIONS);
        _output_collections_path = path_list[OUTPUT_COLLECTIONS];//store a copy of the path in the object
        _full_path = _output_collections_path / (filename+".txt");
        //TODO check if the file already exists
        _ofs.open(_full_path,std::ios_base::out);
        if(!_ofs.is_open()) {
            std::cerr << "Error : Failed to open " << _full_path.string() << std::endl;
            exit(1);
        }
    }

    ~OutputCollection() {
        _ofs.close();
        if(_remove_if_empty && _nb_entries==0) {
            std::filesystem::remove(_full_path);
        }
    }

    void new_entry(std::filesystem::path entry) {
        _ofs << std::filesystem::relative(entry,_output_collections_path).string() << std::endl;
        _nb_entries++;
    }

    void new_comments(std::string str) {
        _ofs << "# " << str << std::endl;
    }

private:
    std::ofstream _ofs;
    std::filesystem::path _full_path;
    std::filesystem::path _output_collections_path;
    unsigned int _nb_entries;
    const bool _remove_if_empty;
};