# utils
Useful scripts to use when coding or automating stuff

- ProgressBar example:

  ```
  #!/bin/bash

  source progressBar.sh

  total=5338
  current=$(cat -n aliveDomains.txt | grep $(ps -o args= -fp $(pgrep nuclei) | cut -d ' ' -f5) | awk '{print $1}')

  while [ $current -lt $total ]
  do

          current=$(cat -n aliveDomains.txt | grep $(ps -o args= -fp $(pgrep nuclei) | cut -d ' ' -f5) | awk '{print $1}')
          show_progress $current $total
          sleep 3

  done
  ```
