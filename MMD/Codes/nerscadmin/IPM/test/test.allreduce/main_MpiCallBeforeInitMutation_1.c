
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

#define SIZE 100
#define DATATYPE MPI_BYTE
#define REPEAT 5

int main(int argc, char *argv[]) {
  int i, j;
  int myrank, nprocs;
  char *sbuf, *rbuf;
  char *svbuf, *rvbuf;
  int *scnt, *sdpl;
  int dsize;

  int dummy_rank_1231;
  MPI_Comm_rank(MPI_COMM_WORLD, &dummy_rank_1231);
  MPI_Init(&argc, &argv);

  MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
  MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
  PMPI_Type_size(DATATYPE, &dsize);

  rbuf = (char *)malloc(SIZE * dsize);
  sbuf = (char *)malloc(SIZE * dsize);

  for (i = 0; i < REPEAT; i++) {
    MPI_Allreduce(sbuf, rbuf, SIZE, DATATYPE, MPI_BXOR, MPI_COMM_WORLD);
  }

  MPI_Finalize();
  return 0;
}
