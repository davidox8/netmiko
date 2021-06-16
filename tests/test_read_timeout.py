from datetime import datetime
import pytest
import time
import re
from netmiko import ConnectHandler
from netmiko.utilities import f_exec_time
from netmiko import ReadTimeout


def my_cleanup(conn, sleep=180):
    try:
        # Must be long enough for "show tech-support" to finish
        time.sleep(sleep)
        conn.disconnect()
    except Exception:
        # If it fails, just try to keep going
        pass


def show_long_running(conn, read_timeout, expect_string):
    start_time = datetime.now()
    my_exception = None
    try:
        conn.send_command(
            "show tech-support", read_timeout=read_timeout, expect_string=expect_string
        )
    except Exception as e:
        my_exception = e
    finally:
        end_time = datetime.now()
        exec_time = end_time - start_time
        # clean-up
        my_cleanup(conn)
        return (my_exception, exec_time)


def show_long_running_notimeout(conn, read_timeout):
    start_time = datetime.now()
    output = conn.send_command("show tech-support", read_timeout=read_timeout)
    end_time = datetime.now()
    exec_time = end_time - start_time
    return (output, exec_time)


def test_read_longrunning_cmd(net_connect_newconn):

    read_timeout = 300
    output, exec_time = show_long_running_notimeout(
        net_connect_newconn, read_timeout=read_timeout
    )
    assert "show interface" in output
    assert exec_time.total_seconds() > 10


@pytest.mark.parametrize(
    "test_timeout,allowed_percentage",
    [(0.4, 5.0), (1, 2.0), (5, 1.0), (10, 0.5), (60, 0.2)],
)
def test_read_timeout(net_connect_newconn, test_timeout, allowed_percentage):

    # Explicitly send expect_string so timing is more accurate
    my_prompt = net_connect_newconn.find_prompt()
    pattern = re.escape(my_prompt)

    my_except, exec_time = show_long_running(
        net_connect_newconn, read_timeout=test_timeout, expect_string=pattern
    )

    # Returned exception should be read_timeout
    assert isinstance(my_except, ReadTimeout)

    # Calculate difference in execution time from timeout
    time_diff = abs(exec_time.total_seconds() - test_timeout)
    # Convert difference to a percentage of expected timeout
    time_margin_percent = time_diff / test_timeout * 100
    # Margin off should be less than the allowed_percentage
    assert time_margin_percent < allowed_percentage


@pytest.mark.parametrize(
    "test_timeout,allowed_percentage", [(1, 2.0), (5, 1.0), (10, 0.5), (60, 0.2)]
)
def test_read_timeout_override(net_connect_newconn, test_timeout, allowed_percentage):

    net_connect_newconn.read_timeout_override = 12
    ssh_conn = net_connect_newconn

    # Explicitly send expect_string so timing is more accurate
    my_prompt = net_connect_newconn.find_prompt()
    pattern = re.escape(my_prompt)

    my_except, exec_time = show_long_running(ssh_conn, read_timeout=test_timeout, expect_string=pattern)

    # Returned exception should be read_timeout
    assert isinstance(my_except, ReadTimeout)

    # For comparsions compare to the override time with a fixed allowed percentage
    test_timeout = ssh_conn.read_timeout_override
    allowed_percentage = 0.5

    # Calculate difference in execution time from read_timeout_override
    time_diff = abs(exec_time.total_seconds() - test_timeout)

    # Convert difference to a percentage of expected timeout
    time_margin_percent = time_diff / test_timeout * 100
    # Margin off should be less than the allowed_percentage
    assert time_margin_percent < allowed_percentage


def test_deprecation_delay_factor(net_connect_newconn):

    ssh_conn = net_connect_newconn
    cmd = "show ip int brief"
    with pytest.deprecated_call():
        ssh_conn.send_command(cmd, delay_factor=2)


def test_deprecation_max_loops(net_connect_newconn):

    ssh_conn = net_connect_newconn
    cmd = "show ip int brief"
    with pytest.deprecated_call():
        ssh_conn.send_command(cmd, max_loops=1000)
