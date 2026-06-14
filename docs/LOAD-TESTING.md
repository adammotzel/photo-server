# Load Testing

Load tests are defined in [tests/load_tests](../tests/load_tests/). 

To run these tests on your instance of the application, first follow the instructions in [docs/POSTGRES-SETUP.md](docs/POSTGRES-SETUP.md) to create a new database, but name it `photoapp_test`. Then seed the test db with users by executing [scripts/tests/create_test_users.py](scripts/tests/create_test_users.py).

# Run Load Tests

Start the app:
```bash
bash scripts/tests/run_test_app.sh
```

Run the tests:
```bash
bash scripts/tests/run_load_tests.sh
```

Run the app and load tests on separate servers/devices. You *can* run both on the same device, but results will be skewed because they'll be competing for the same CPU, memory, etc.

Follow [Locust's documentation](https://docs.locust.io/en/stable/quickstart.html) if you want to create more load tests.
