#!/bin/bash
directory="$(pwd)"
output=practica1

# Creamos el fichero pdf
docker run --name temppandoc -v \
          "$directory":/source jagregory/pandoc \
          --variable title="Tipología y ciclo de vida de los datos" \
          --variable subtitle="Práctica 1" \
          --variable author="[Fernando Rodríguez López]" \
          --variable date="08/04/2018" \
          --variable subject="webscraping" \
          --variable keywords="[webscraping, UOC]" \
          --variable titlepage=true \
          --variable toc-own-page=true \
          --variable titlepage-text-color="000078" \
          --variable titlepage-rule-color="000078" \
          --variable titlepage-rule-height=2 \
          --variable uoc="images/logo-uoc-default.png" \
          --variable logo="images/candidates.png" \
          --variable header-right="Fernando Rodríguez López" \
          --variable footer-left="08/04/2018" \
          -f markdown \
          -t latex  README.md \
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

#
# ---
# title: "Tipología y ciclo de vida de los datos"
# subtitle: "Práctica 1"
# author: [Fernando Rodríguez López]
# date: "08/04/2018"
# subject: "webscraping"
# keywords: [webscraping, UOC]
# titlepage: true
# toc-own-page: true
# titlepage-text-color: "000078"
# titlepage-rule-color: "000078"
# titlepage-rule-height: 2
# uoc: "images/logo-uoc-default.png"
# logo: "images/candidates.png"
# header-right: "Fernando Rodríguez López"
# footer-left: "08/04/2018"
# ...
