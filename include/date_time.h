#pragma once

#include <ctime>
#include <cstdio>

#define ABSOLUTE_YEAR(Epoch_based_year) ((Epoch_based_year)+1900)
#define ONE_BASED_MONTH(zero_based_month) ((zero_based_month)+1)

class DateTimeStr {

public:
    DateTimeStr() {
        time_t date_time = time(NULL);
        struct tm *dt_struct = localtime(&date_time);
        sprintf(_pretty_string,"%04d-%02d-%02d %02d:%02d:%02d",
                ABSOLUTE_YEAR(dt_struct->tm_year),
                ONE_BASED_MONTH(dt_struct->tm_mon),
                dt_struct->tm_mday,
                dt_struct->tm_hour,
                dt_struct->tm_min,
                dt_struct->tm_sec);
        sprintf(_filename_string,"%04d%02d%02d_%02d%02d%02d",
                ABSOLUTE_YEAR(dt_struct->tm_year),
                ONE_BASED_MONTH(dt_struct->tm_mon),
                dt_struct->tm_mday,
                dt_struct->tm_hour,
                dt_struct->tm_min,
                dt_struct->tm_sec);
    }

    const char* pretty_string() {
        return _pretty_string;
    }

    const char* filename_string() {
        return _filename_string;
    }

private:
    char _pretty_string[19+1];
    char _filename_string[15+1];
};