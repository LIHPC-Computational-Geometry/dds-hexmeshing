#include <iostream>

#include "paths.h"
#include "collections.h"

int main(int argc, char *argv[]) {
    paths p;
    std::cout << "shared_data = " << p.shared_data() << std::endl;

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(p.shared_data() / "MAMBO_CAD.txt",input_folders,subcollections)) {
        //an error occured
        return 1;
    }

    std::cout << "Set of input folders (" << input_folders.size() << " elements):" << std::endl;
    for(auto& p : input_folders) {
        std::cout << p.string() << std::endl;
    }

    return 0;
}