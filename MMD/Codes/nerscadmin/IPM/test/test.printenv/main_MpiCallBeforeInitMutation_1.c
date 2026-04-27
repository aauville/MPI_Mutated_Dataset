
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char *argv[], char **envp) {
  int myrank, nprocs;

  char **env;
  int dummy_rank_1231;
  MPI_Comm_rank(MPI_COMM_WORLD, &dummy_rank_1231);
  MPI_Init(&argc, &argv);

  MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
  MPI_Comm_size(MPI_COMM_WORLD, &nprocs);

  for (env = envp; *env != 0; env++) {
    fprintf(stderr, "%d of %d:%s\n", myrank, nprocs, (*env));
  }

  MPI_Finalize();
  return 0;
}
