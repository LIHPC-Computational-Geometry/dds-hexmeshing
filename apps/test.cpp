#include <iostream>

#include "paths.h"

int main(int argc, char *argv[]) {
    paths p;
    std::cout << "shared_data = " << p.shared_data() << std::endl;

    return 0;
}