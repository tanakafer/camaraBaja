#!/bin/bash
directory="$(pwd)"
output=practica1

# Creamos el fichero pdf
docker run --name temppandoc -v \
          "$directory":/source jagregory/pandoc \
          -f markdown \
          -t latex README.md \
          --template uoc.tex \
          --listing \
          -o $output.pdf
docker rm temppandoc
echo "Creado fihero pdf"


# Creamos el fichero docx
docker run --name temppandoc -v \
          "$directory":/source jagregory/pandoc \
          -f markdown \
          -t docx README.md \
          -o $output.docx
docker rm temppandoc
echo "Creado fihero docx"
