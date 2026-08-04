#!/bin/bash

locust -f tests/load_tests/locustfile.py --host=https://localhost:8000
