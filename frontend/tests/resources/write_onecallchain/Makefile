ifdef ENABLE_PREFETCH
	DENABLE_PREFETCH = -DENABLE_CODE_PREFETCH
endif

benchmark: 0.o main.o
	$(CC) -o benchmark 0.o main.o $(DENABLE_PREFETCH) -O0

0.o: 0.c
	$(CC) -c -o 0.o 0.c $(DENABLE_PREFETCH) -O0

main.o: main.c
	$(CC) -c -o main.o main.c $(DENABLE_PREFETCH) -O0

clean:
	rm *.o benchmark
