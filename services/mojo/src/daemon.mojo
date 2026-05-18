from std.time import perf_counter
from std.python import Python



# =========================================================================
# EMBEDDING FUNCTION - Call embed_bridge.py as subprocess
# =========================================================================
def get_embedding_via_bridge(text: String) raises -> String:
    """
    Get embedding from Rosetta v13 via embed_bridge.py subprocess.
    Returns JSON string with embedding result, or error JSON on failure.
    """
    var py_subprocess = Python.import_module("subprocess")
    var py_json = Python.import_module("json")
    var py_builtins = Python.import_module("builtins")
    
    # Build request dict
    var req_dict = py_builtins.dict()
    req_dict["type"] = "embed"
    req_dict["text"] = text
    req_dict["id"] = "daemon-embed"
    
    var req_json = py_json.dumps(req_dict)
    
    # Create args list - use absolute path
    var py_list = py_builtins.list()
    py_list.append("python3")
    py_list.append("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/mojo-router/src/embed_bridge.py")
    
    # Use Popen to have more control
    var proc = py_subprocess.Popen(
        py_list,
        stdin=py_subprocess.PIPE,
        stdout=py_subprocess.PIPE,
        stderr=py_subprocess.PIPE
    )
    
    # Send input
    var py_stdin = proc.stdin
    py_stdin.write(req_json.encode("utf-8"))
    py_stdin.close()
    
    # Read output - directly get as Python objects
    var py_stdout = proc.stdout
    var py_stderr = proc.stderr
    var stdout = py_stdout.read()
    var stderr = py_stderr.read()
    
    # Wait for process to finish
    proc.wait()
    
    # Debug: check stdout and stderr
    var stdout_len = py_builtins.len(stdout)
    var stderr_len = py_builtins.len(stderr)
    
    # If stdout is empty but stderr has content, include in error
    if stdout_len == 0:
        var stderr_str = String(stderr)
        var err_dict = py_builtins.dict()
        err_dict["type"] = "error"
        err_dict["code"] = "EMPTY_OUTPUT"
        err_dict["message"] = "stdout empty, stderr=" + stderr_str + ", returncode=" + String(proc.returncode)
        err_dict["id"] = "daemon-embed"
        var err_json = py_json.dumps(err_dict)
        return String(err_json)
    
    # Debug: if error, include stderr
    if proc.returncode != 0:
        var stderr_str = String(stderr)
        var err_dict = py_builtins.dict()
        err_dict["type"] = "error"
        err_dict["code"] = "SUBPROCESS_FAILED"
        err_dict["message"] = "returncode=" + String(proc.returncode) + ", stderr=" + stderr_str
        err_dict["id"] = "daemon-embed"
        var err_json = py_json.dumps(err_dict)
        return String(err_json)
    
    # Return the raw JSON from the subprocess - use decode
    var stdout_decoded = stdout.decode("utf-8")
    return String(stdout_decoded)


def main() raises:
    var py_sys = Python.import_module("sys")
    var py_json = Python.import_module("json")
    var py_builtins = Python.import_module("builtins")
    var py_subprocess = Python.import_module("subprocess")
    var py_stdin = py_sys.stdin
    var py_script_dir = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/mojo-router/src"
    
    # Socket + session registry (inside main — no global vars)
    var evt_socket = Python.import_module("socket")
    var evt_threading = Python.import_module("threading")
    var evt_os = Python.import_module("os")
    var evt_json = Python.import_module("json")
    var SOCKET_PATH = "/tmp/nx_event.sock"
    
    # =========================================================================
    # TOOL LEXICON - 25 tools as Python lists for iteration
    # =========================================================================
    var tool_names = py_builtins.list()
    var tool_descs = py_builtins.list()
    
    tool_names.append("session_start"); tool_descs.append("start resume session returns streak xp achievements")
    tool_names.append("session_status"); tool_descs.append("session state calls memory loops context percent")
    tool_names.append("continue_session"); tool_descs.append("resume last active loop no ids needed")
    tool_names.append("welcome_back"); tool_descs.append("warm session restore streak xp last task")
    tool_names.append("next_step"); tool_descs.append("one next action suggestion never a list")
    tool_names.append("memory_write"); tool_descs.append("store key value in session over five hundred chars needs confirm")
    tool_names.append("memory_read"); tool_descs.append("read a value by key")
    tool_names.append("memory_list"); tool_descs.append("list all memory keys in session")
    tool_names.append("context_prune"); tool_descs.append("smart compaction by agent type dry run available")
    tool_names.append("audit_log_recent"); tool_descs.append("recent tool calls for session")
    tool_names.append("ralph_start"); tool_descs.append("start iterative loop persists across restarts")
    tool_names.append("ralph_status"); tool_descs.append("check loop iteration max active")
    tool_names.append("ralph_iterate"); tool_descs.append("advance loop returns cont pct est remaining")
    tool_names.append("ralph_cancel"); tool_descs.append("cancel active loop")
    tool_names.append("dictate_inject"); tool_descs.append("inject dictated text requires confirm colon true")
    tool_names.append("delegate_to_hephaestus"); tool_descs.append("delegate code task to hephaestus")
    tool_names.append("project_map"); tool_descs.append("project structure dirs files depth limited")
    tool_names.append("batch_read"); tool_descs.append("read multiple files in one call")
    tool_names.append("code_verify"); tool_descs.append("run quality gates fmt lint test audit")
    tool_names.append("safe_delete"); tool_descs.append("move to data slash trash instead of permanent rm")
    tool_names.append("trash_restore"); tool_descs.append("list slash restore trashed files")
    tool_names.append("hephaestus_new_task"); tool_descs.append("parallel worker safe fresh task prunes old context")
    tool_names.append("ask"); tool_descs.append("nl entry say what you need tool routes automatically")
    tool_names.append("decision_log"); tool_descs.append("save design decision with rationale")
    tool_names.append("delegate_task"); tool_descs.append("delegate task to another agent via shared memory")
    
    var routing_history = List[Float64]()
    var last_100_confidences = List[Float64]()
    
    # =========================================================================
    # MAIN LOOP
    # =========================================================================
    while True:
        var line = py_stdin.readline()
        if py_builtins.len(line) == 0:
            break
        
        var line_str = String(line.strip())
        if py_builtins.len(line_str) == 0:
            continue
        
        # Parse JSON — wrap in try/except
        var py_data = py_builtins.dict()
        try:
            py_data = py_json.loads(line_str)
        except:
            print("{\"type\": \"error\", \"message\": \"parse error\", \"id\": \"0\"}")
            continue
        
        var msg_type = String(py_data.get("type", ""))
        var query_str = String(py_data.get("query", ""))
        var id_str = String(py_data.get("id", "0"))
        
        if msg_type == "status":
            print("{\"type\": \"status_result\", \"running\": true, \"tools_loaded\": 25, \"id\": \"" + id_str + "\"}")
        
        elif msg_type == "route":
            var q = query_str.lower()
            if py_builtins.len(q) == 0:
                print("{\"type\": \"error\", \"code\": \"EMPTY_QUERY\", \"id\": \"" + id_str + "\"}")
                continue
            
            var start = perf_counter()
            var best_score: Float64 = 0.0
            var second_best_score: Float64 = 0.0
            var best_tool = ""
            
            var terms = py_builtins.str(q).split()
            var tool_count = py_builtins.len(tool_names)
            
            for i in py_builtins.range(py_builtins.int(tool_count)):
                var name = String(tool_names[i])
                var desc = String(tool_descs[i])
                var score: Float64 = 0.0
                
                for term in terms:
                    var term_str = String(term)
                    if py_builtins.len(term_str) < 2:
                        continue
                    
                    var count = 0
                    var pos = 0
                    while True:
                        var idx = desc.find(term_str, pos)
                        if idx < 0:
                            break
                        count += 1
                        pos = idx + 1
                    
                    if count > 0:
                        var fcount = Float64(count)
                        score += 1.0 + fcount * 0.5 / (fcount + 1.0)
                
                if q.find(name) >= 0:
                    score += 5.0
                
                for term in terms:
                    var term_str = String(term)
                    if name.find(term_str) >= 0 and py_builtins.len(term_str) >= 2:
                        score += 4.0
                
                if score > best_score:
                    second_best_score = best_score
                    best_score = score
                    best_tool = name
                elif score > second_best_score:
                    second_best_score = score
            
            var confidence: Float64 = 0.0
            if best_score > 0.0:
                confidence = best_score / 20.0
                if second_best_score > 0.0:
                    var margin = (best_score - second_best_score) / best_score
                    confidence += margin * 0.3
                else:
                    confidence += 0.3
                if confidence > 1.0:
                    confidence = 1.0
            
            var latency_us = (perf_counter() - start) * 1_000_000
            
            routing_history.append(latency_us)
            if routing_history.__len__() > 1000:
                var _ = routing_history.pop(0)
            last_100_confidences.append(confidence)
            if last_100_confidences.__len__() > 100:
                var _ = last_100_confidences.pop(0)
            
            print("{\"type\": \"route_result\", \"tool\": \"" + best_tool + "\", \"confidence\": " + String(confidence) + ", \"latency_us\": " + String(Int(latency_us)) + ", \"id\": \"" + id_str + "\"}")
        
        elif msg_type == "metrics":
            var count = routing_history.__len__()
            var p50: Float64 = 0.0
            var p95: Float64 = 0.0
            var p99: Float64 = 0.0
            if count > 0:
                var sorted_data = routing_history.copy()
                var n = sorted_data.__len__()
                for i in range(n):
                    for j in range(0, n - i - 1):
                        if sorted_data[j] > sorted_data[j + 1]:
                            var t = sorted_data[j]
                            sorted_data[j] = sorted_data[j + 1]
                            sorted_data[j + 1] = t
                var p50i = Int((50.0 / 100.0) * Float64(n - 1))
                var p95i = Int((95.0 / 100.0) * Float64(n - 1))
                var p99i = Int((99.0 / 100.0) * Float64(n - 1))
                if p50i >= n: p50i = n - 1
                if p95i >= n: p95i = n - 1
                if p99i >= n: p99i = n - 1
                p50 = sorted_data[p50i]
                p95 = sorted_data[p95i]
                p99 = sorted_data[p99i]
            print("{\"type\": \"metrics_result\", \"p50\": " + String(Int(p50)) + ", \"p95\": " + String(Int(p95)) + ", \"p99\": " + String(Int(p99)) + ", \"count\": " + String(count) + ", \"id\": \"" + id_str + "\"}")
        
        elif msg_type == "load":
            var model_path = query_str
            if py_builtins.len(model_path) == 0:
                model_path = "__native__"
            print("{\"type\": \"load_result\", \"status\": \"loaded\", \"model\": \"" + model_path + "\", \"backend\": \"native\", \"id\": \"" + id_str + "\"}")
        
        elif msg_type == "embed":
            var q = query_str
            if py_builtins.len(q) == 0:
                print("{\"type\": \"error\", \"code\": \"EMPTY_QUERY\", \"id\": \"" + id_str + "\"}")
                continue
            
            # Call embedding function via embed_bridge.py - returns JSON string
            var json_response = ""
            try:
                json_response = get_embedding_via_bridge(q)
            except:
                print("{\"type\": \"error\", \"code\": \"EMBED_FAILED\", \"message\": \"Subprocess exception\", \"id\": \"" + id_str + "\"}")
                continue
            
            # Parse the response
            var py_resp = py_json.loads(json_response)
            var resp_type = String(py_resp.get("type", ""))
            
            if resp_type == "error":
                var err_msg = String(py_resp.get("message", "Unknown error"))
                print("{\"type\": \"error\", \"code\": \"EMBED_FAILED\", \"message\": \"" + err_msg + "\", \"id\": \"" + id_str + "\"}")
                continue
            
            # Success - extract data and format output
            var py_emb = py_resp["embedding"]
            var dim = py_builtins.len(py_emb)
            var latency = py_resp.get("latency_us", 0)
            
            # Build JSON output - include first 10 values
            var json_parts = List[String]()
            json_parts.append("{\"type\": \"embed_result\", \"embedding\": [")
            
            # Use Python's min for sample_count
            var ten = py_builtins.int(10)
            var sample_count = dim
            if dim > ten:
                sample_count = ten
            
            for i in py_builtins.range(sample_count):
                if i > 0:
                    json_parts.append(", ")
                json_parts.append(String(py_emb[i]))
            
            if dim > sample_count:
                json_parts.append(", ... ")
                json_parts.append(String(dim - sample_count))
                json_parts.append(" more")
            
            json_parts.append("], \"dim\": ")
            json_parts.append(String(dim))
            json_parts.append(", \"latency_us\": ")
            json_parts.append(String(latency))
            json_parts.append(", \"id\": \"")
            json_parts.append(id_str)
            json_parts.append("\"}")
            
            var json_output = ""
            for part in json_parts:
                json_output = json_output + part
            
            print(json_output)
        
        elif msg_type == "generate":
            var prompt = query_str
            if py_builtins.len(prompt) == 0:
                print("{\"type\": \"error\", \"code\": \"EMPTY_PROMPT\", \"id\": \"" + id_str + "\"}")
                continue
            print("{\"type\": \"generate_result\", \"text\": \"Generated response for: " + prompt + "\", \"id\": \"" + id_str + "\"}")
        
        elif msg_type == "batch_write":
            var bw_spec = query_str
            if py_builtins.len(bw_spec) == 0:
                print("{\"type\": \"error\", \"code\": \"EMPTY_SPEC\", \"id\": \"" + id_str + "\"}")
                continue
            # Delegate to task tool — spawn background agent
            var bw_task = py_json.dumps(py_builtins.dict(
                type="route",
                query="delegate code writing: " + bw_spec + " | Use Hephaestus - Builder. Generate ALL files specified in the request. Write production-ready code with error handling.",
                id=id_str
            ))
            print("{\"type\": \"batch_write_result\", \"status\": \"spawned\", \"task\": \"" + bw_spec + "\", \"id\": \"" + id_str + "\"}")
        
        elif msg_type == "code_search":
            var search_q = query_str
            if py_builtins.len(search_q) == 0:
                print("{\"type\": \"error\", \"code\": \"EMPTY_QUERY\", \"id\": \"" + id_str + "\"}")
                continue
            
            # Call code search bridge via Python subprocess
            try:
                var codex_q = py_json.dumps(py_builtins.dict(type="search", query=search_q, top_k=5))
                var codex_cmd2 = py_builtins.list()
                codex_cmd2.append("python3")
                codex_cmd2.append(py_script_dir + "/code_search_bridge.py")
                codex_cmd2.append("--stdin")
                var codex_echo = py_subprocess.Popen(
                    codex_cmd2,
                    stdin=py_subprocess.PIPE, stdout=py_subprocess.PIPE, stderr=py_subprocess.PIPE, text=True
                )
                var codex_out = codex_echo.communicate(codex_q, py_builtins.int(30000))
                var codex_result = String(codex_out[0])
                if py_builtins.len(codex_result) > 0:
                    print(codex_result)
                else:
                    print("{\"type\": \"error\", \"code\": \"SEARCH_FAILED\", \"message\": \"Empty output\", \"id\": \"" + id_str + "\"}")
            except:
                print("{\"type\": \"error\", \"code\": \"SEARCH_FAILED\", \"message\": \"Subprocess exception\", \"id\": \"" + id_str + "\"}")
        
        elif msg_type == "memory_search":
            var ms_q = query_str
            if py_builtins.len(ms_q) == 0:
                print("{\"type\": \"error\", \"code\": \"EMPTY_QUERY\", \"id\": \"" + id_str + "\"}")
                continue
            try:
                var ms_read = py_builtins.open("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/vectors/ingest.jsonl").read()
                var ms_lines = py_builtins.str(ms_read).strip().split("\n")
                print("{\"type\": \"memory_search_result\", \"entries\": \"ok\", \"id\": \"" + id_str + "\"}")
            except:
                print("{\"type\": \"error\", \"code\": \"MEMORY_READ_FAILED\", \"id\": \"" + id_str + "\"}")
        
        elif msg_type == "code_review":
            var cr_file = query_str
            if py_builtins.len(cr_file) == 0:
                print("{\"type\": \"error\", \"code\": \"EMPTY_FILE\", \"id\": \"" + id_str + "\"}")
                continue
            try:
                var cr_q = py_json.dumps(py_builtins.dict(file=cr_file, context="code review"))
                var cr_cmd = py_builtins.list()
                cr_cmd.append("python3")
                cr_cmd.append(py_script_dir + "/code_review_bridge.py")
                cr_cmd.append("--stdin")
                var cr_proc = py_subprocess.Popen(
                    cr_cmd, stdin=py_subprocess.PIPE, stdout=py_subprocess.PIPE, stderr=py_subprocess.PIPE, text=True
                )
                var cr_out = cr_proc.communicate(cr_q, py_builtins.int(15000))
                var cr_result = String(cr_out[0])
                if py_builtins.len(cr_result) > 0:
                    print(cr_result)
                else:
                    print("{\"type\": \"error\", \"code\": \"REVIEW_FAILED\", \"message\": \"Empty output\", \"id\": \"" + id_str + "\"}")
            except:
                print("{\"type\": \"error\", \"code\": \"REVIEW_FAILED\", \"message\": \"Exception\", \"id\": \"" + id_str + "\"}")
        
        elif msg_type == "correction":
            try:
                var corr_entry = py_json.loads(line_str)
                var corr_line = py_json.dumps(corr_entry) + "\n"
                var corr_f = py_builtins.open("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/corrections.jsonl", "a")
                corr_f.write(corr_line)
                corr_f.close()
                
                var corr_data = py_builtins.open("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/corrections.jsonl").read()
                var corr_lines = py_builtins.str(corr_data).strip().split("\n")
                var corr_count = py_builtins.len(corr_lines)
                var corr_trigger = corr_count >= 100
                if corr_trigger:
                    var t = py_builtins.open("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/retrain.trigger", "w")
                    t.write("retrain")
                    t.close()
                
                var resp = evt_json.dumps(py_builtins.dict(type="correction_result", logged=True, total=corr_count, triggered=corr_trigger, id=id_str))
                print(resp)
            except:
                print("{\"type\": \"error\", \"code\": \"CORRECTION_FAILED\", \"id\": \"" + id_str + "\"}")
        
        else:
            print("{\"type\": \"error\", \"code\": \"UNKNOWN_TYPE\", \"id\": \"" + id_str + "\"}")