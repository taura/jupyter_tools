#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <assert.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <err.h>

int main(int argc, char ** argv) {
  char * pid = argv[1];
  char * cgroup_procs = (argc > 2 ? argv[2] : "/sys/fs/cgroup/taulec/tau/cgroup.procs");
  size_t count = strlen(pid);
  int fd = open(cgroup_procs, O_WRONLY);
  if (fd == -1) { err(1, "open"); }
  ssize_t sz = write(fd, pid, count);
  if (sz != (ssize_t)count) { err(1, "write"); }
  close(fd);
  return 0;
}
