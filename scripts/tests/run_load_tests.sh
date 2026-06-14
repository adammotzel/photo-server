#!/bin/bash

locust -f tests/load_tests/locustfile.py --host=http://localhost:8000
