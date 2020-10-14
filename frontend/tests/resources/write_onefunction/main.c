#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include "headers.h"


int main(int argc, char **argv) {
unsigned long loops = 1;
int c;
while ((c = getopt(argc, argv, "l:")) != -1) {
switch (c) {
case 'l':
loops = strtoul(optarg, NULL, 0);
break;
default:
printf("Invalid argument provided. Valid arguments: -l\n");
exit(1);
}
}
for (int i = 0; i < loops; i++) {
function_19();
}
}
