#!/bin/bash
docker build -t app .
docker run -it --rm --name app -p 8000:5000 app
