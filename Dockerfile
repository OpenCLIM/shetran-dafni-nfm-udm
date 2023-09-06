FROM python:slim

# Install required Fortran
RUN apt update -y
RUN apt upgrade -y
RUN apt install -y gfortran

RUN mkdir /src

WORKDIR /src

# Move the executables and libraries into the workflow folder
COPY shetran/shetran-linux shetran/shetran-prepare-snow run.py shetran/shetran-setup-UDM-linux shetran/shetran-setup-CEH2Types-linux ./
COPY shetran/lib /usr/lib/

# Change the permissions on the executables:
RUN chmod +x shetran-prepare-snow
RUN chmod +x shetran-linux
RUN chmod +x shetran-setup-UDM-linux
RUN chmod +x shetran-setup-CEH2Types-linux

# Run the python script that executes the python edits and exe's:
CMD python run.py
