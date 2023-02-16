# Building the docker image
#### For systems with docker already installed and using BASH
#### Originally tested and designed for use on ubuntu 22.04
- First, give permissions to run the `make_ion_image.sh` file by running 
  `chmod +x make_ion_image.sh` from within the `ION_GNS3_netsim/docker_resources` directory
- Now, if a differing version of ION is needed or you wish to add anything to the image, modify the file `ION_GNS3_netsim/docker_resources/dockercontext/dockerfile`
  - to change what version of ION is being used, change the url  found on line 13 to direct to your desired sipped ION version.
  - alternatively, to install ION to the image based on a local modified version, first zip your local version using 
    - tar -czvf \<output zipped archive name\> \<input directories and files\>
    - Then change line 13 from a `wget` call as it is by default to be `COPY <output zipped archive name> /` and modify line 15 from `RUN tar -xvzf download` to be `RUN tar -xvzf <output zipped archive name>`
- If a differing name for the image is desired, then modify the `NAME` field within make_ion_image.sh
- Finally, run the script 
  - from the `ION_GNS3_netsim/docker_resources` directory, the command would be `./make_ion_image.sh`
# Creating a GNS3 template from the docker image
- Open GNS3
- Select `File` -> `New Template` from the menu in the top left
- Select `Manually create a new template` then click `Next`
- Select `Docker` -> `Docker Containers` from the menu on the left
- Select `New`
- Ensure `Existing Image` is selected, then select the image you wish to use from the dropdown menu
  - If the name was not modified in the make_ion_image.sh script when building the image, it will be named `sspringe/ion_node_ubuntu_latest:1.1` 
- Select `Next` 
- (Optional) Update the name to use for the template
- Select `Next`
- Enter the number of Adapters/Interfaces you owuld like each node to have
  - I recommend 4 or 8 for moderate networks, but size this to your specific needs.
- Select `Next`
- Select `Next`
- Select `Finish`
- Apply changes and close the template window
