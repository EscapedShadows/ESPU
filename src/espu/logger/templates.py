simple_template = "[{{log_level.up}}] {{msg}}"
timing_template = (
    "[{{ctime.format('%H:%M:%S')}}] "
    "[{{log_level.up}}] "
    "Elapsed: {{time_since_start:.3f}}s | "
    "{{msg}}"
    )
informational_template = (
    "[{{log_level.up}}] "
    "Filename: {{filename}} | "
    "Line Number: {{lineno}} | "
    "Function Name: {{funcName}} | "
    "Thread Name: {{threadName}} | "
    "Full Path: {{pathname}} | "
    "{{msg}}"
)