#pragma once

#include <ctime>
#include <cstdio>
#include <sys/stat.h>
#include <filesystem>
#include <string.h>
#include <exception>

// yes, time management is more straightforward in C than in C++ 17

#define ABSOLUTE_YEAR(Epoch_based_year) ((Epoch_based_year)+1900)
#define ONE_BASED_MONTH(zero_based_month) ((zero_based_month)+1)

class DateTimeStr {

public:
    DateTimeStr() : _pretty_string(""), _filename_string("") {
        time_t date_time = time(NULL);
        struct tm *tmp = localtime(&date_time);//data pointed by tmp may change
        memcpy(&_dt_struct,tmp,sizeof(struct tm));//local copy
    }

    //date of last modification
    DateTimeStr(std::filesystem::path path) : _pretty_string(""), _filename_string("") {
        if(!std::filesystem::exists(path)) {
            throw std::runtime_error("Error: " + path.string() + " is missing");
        }
        struct stat file_stats;
        if(stat(path.string().c_str(),&file_stats)) {
            throw std::runtime_error("Error: unable to get date of last modification for " + path.string());
        }
        struct tm *tmp = localtime(&file_stats.st_mtime);//data pointed by tmp may change
        memcpy(&_dt_struct,tmp,sizeof(struct tm));//local copy
    }

    // "YYYY/MM/DD hh:mm:ss"
    const char* pretty_string() {
        if(strcmp(_pretty_string,"")==0) { // if _pretty_string is empty
            sprintf(_pretty_string,"%04d/%02d/%02d %02d:%02d:%02d",
                    ABSOLUTE_YEAR(_dt_struct.tm_year),
                    ONE_BASED_MONTH(_dt_struct.tm_mon),
                    _dt_struct.tm_mday,
                    _dt_struct.tm_hour,
                    _dt_struct.tm_min,
                    _dt_struct.tm_sec);
        }
        return _pretty_string;
    }

    // compact form without special chars:
    // "YYYYMMDD_hhmmss"
    const char* filename_string() {
        if(strcmp(_filename_string,"")==0) { // if _filename_string is empty
            sprintf(_filename_string,"%04d%02d%02d_%02d%02d%02d",
                    ABSOLUTE_YEAR(_dt_struct.tm_year),
                    ONE_BASED_MONTH(_dt_struct.tm_mon),
                    _dt_struct.tm_mday,
                    _dt_struct.tm_hour,
                    _dt_struct.tm_min,
                    _dt_struct.tm_sec);
        }
        return _filename_string;
    }

private:
    struct tm _dt_struct;// C date-time struct
    char _pretty_string[19+1];
    char _filename_string[15+1];
};