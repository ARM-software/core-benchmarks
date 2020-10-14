benchmark: 0.o main.o
	gcc -o benchmark 0.o main.o -O0

0.o: 0.c
	gcc -c -o 0.o 0.c -O0

main.o: main.c
	gcc -c -o main.o main.c -O0

clean:
	rm *.o benchmark
