// javaCompletions.js (9+/10 edition)
//
// Curated Java completions/snippets for Monaco (no full LSP required).
// - Focus: common programming-challenge patterns (DS, algo templates, fast I/O).
// - Optional: "system" APIs (files/network/process) behind a toggle.
//
// Usage:
// 1) Load this file after Monaco loads.
// 2) Call: window.registerJavaCompletions();
//
// Notes:
// - Safe to call multiple times (disposes previous provider).
// - Provider is language-level ("java"), so you DO NOT need to pass an editor instance.

(function () {
  // Safe enums so this file can be loaded before Monaco.
  // Monaco (and VS Code) use numeric enums; we only need a few for UI icons.
  const __KIND = {
    Function: 2,   // CompletionItemKind.Function
    Keyword: 13,   // CompletionItemKind.Keyword
    Snippet: 14,   // CompletionItemKind.Snippet
  };
  const __INSERT_AS_SNIPPET = 4; // CompletionItemInsertTextRule.InsertAsSnippet

  "use strict";

  // --- Toggle for potentially-disallowed APIs in many online judges/sandboxes ---
  const ENABLE_SYSTEM_APIS = false; // set true if your sandbox allows process/files/network

  const lower = (s) => (s || "").toString().toLowerCase();

  function getLinePrefix(model, position) {
    return model.getValueInRange({
      startLineNumber: position.lineNumber,
      startColumn: 1,
      endLineNumber: position.lineNumber,
      endColumn: position.column,
    });
  }

  function getWordAndRange(model, position) {
    const w = model.getWordUntilPosition(position);
    const range = new monaco.Range(position.lineNumber, w.startColumn, position.lineNumber, w.endColumn);
    return { word: w.word || "", range };
  }

  function snippet(label, insertText, detail, documentation, sortText, filterText, preselect) {
    return {
      label,
      kind: __KIND.Snippet,
      insertText,
      insertTextRules: __INSERT_AS_SNIPPET,
      detail,
      documentation,
      sortText,
      filterText: filterText || label,
      preselect: !!preselect,
    };
  }

  function func(label, insertText, detail, documentation, sortText, filterText) {
    return {
      label,
      kind: __KIND.Function,
      insertText,
      insertTextRules: __INSERT_AS_SNIPPET,
      detail,
      documentation,
      sortText,
      filterText: filterText || label,
    };
  }

  function kw(label, insertText, detail, documentation, sortText, filterText) {
    return {
      label,
      kind: __KIND.Keyword,
      insertText,
      insertTextRules: __INSERT_AS_SNIPPET,
      detail,
      documentation,
      sortText,
      filterText: filterText || label,
    };
  }

  function asSuggestions(metas, range) {
    return metas.map((m) => ({ ...m, range }));
  }

  // ---------------------- catalogs ----------------------

  // High-signal, always useful.
  const TOP = [
    func("System.out.println", "System.out.println(${1:msg});", "Print line", "stdout + newline", "0_top_001", "println print sysout"),
    func("System.out.print", "System.out.print(${1:msg});", "Print", "stdout (no newline)", "0_top_002", "print sysout"),
    func("System.err.println", "System.err.println(${1:msg});", "Print error", "stderr + newline", "0_top_003", "stderr err println"),

    snippet("import (contest defaults)", "import java.io.*;\nimport java.util.*;\n\n$0", "Common imports", "Typical contest imports", "0_top_010", "import util io", true),
    snippet("import + Math/Streams", "import java.io.*;\nimport java.util.*;\nimport java.util.stream.*;\n\n$0", "Contest + streams", "", "0_top_011", "import stream"),
    snippet("class Main + main()", "public class Main {\n\tpublic static void main(String[] args) throws Exception {\n\t\t$0\n\t}\n}\n", "Main skeleton", "Common for I/O style problems", "0_top_020", "main class"),
    snippet("class Solution (LeetCode)", "class Solution {\n\t$0\n}\n", "Solution class", "LeetCode/online judge style", "0_top_021", "solution class"),

    snippet("StringBuilder sb", "StringBuilder sb = new StringBuilder();\n$0", "StringBuilder", "Fast output building", "0_top_030", "stringbuilder sb"),
    snippet("HashMap freq", "Map<${1:K}, Integer> freq = new HashMap<>();\n$0", "Frequency map", "Common counting pattern", "0_top_040", "freq map hashmap"),
    snippet("int[] arr = new int[n]", "int[] arr = new int[${1:n}];\n$0", "Array allocate", "Allocate array", "0_top_050", "int[] array"),
  ];

  // Control flow.
  const FLOW = [
    kw("if", "if (${1:condition}) {\n\t$0\n}\n", "If statement", "", "1_flow_001", "if"),
    kw("if/else", "if (${1:condition}) {\n\t$2\n} else {\n\t$0\n}\n", "If / else", "", "1_flow_002", "if else"),
    kw("else if", "else if (${1:condition}) {\n\t$0\n}\n", "Else-if", "", "1_flow_003", "else if"),
    kw("switch", "switch (${1:value}) {\n\tcase ${2:CONST}:\n\t\t$0\n\t\tbreak;\n\tdefault:\n\t\tbreak;\n}\n", "Switch statement", "", "1_flow_004", "switch case"),
    kw("for (i=0; i<n; i++)", "for (int ${1:i} = 0; ${1:i} < ${2:n}; ${1:i}++) {\n\t$0\n}\n", "For loop", "", "1_flow_010", "for loop"),
    kw("for-each", "for (${1:Type} ${2:x} : ${3:iterable}) {\n\t$0\n}\n", "Enhanced for", "", "1_flow_011", "foreach for each"),
    kw("while", "while (${1:condition}) {\n\t$0\n}\n", "While loop", "", "1_flow_012", "while"),
    kw("do/while", "do {\n\t$0\n} while (${1:condition});\n", "Do/while loop", "", "1_flow_013", "do while"),
    snippet("return early", "if (${1:badCase}) return ${2:ans};\n$0", "Guard clause", "Early return to reduce nesting", "1_flow_020", "guard return"),
    snippet("try/catch", "try {\n\t$1\n} catch (${2:Exception} ${3:e}) {\n\t$0\n}\n", "Try/catch", "", "1_flow_030", "try catch"),
  ];

  // Data structures.
  const DS = [
    snippet("ArrayList<>", "List<${1:T}> ${2:list} = new ArrayList<>();\n$0", "ArrayList", "", "2_ds_001", "arraylist list"),
    snippet("HashMap<>", "Map<${1:K}, ${2:V}> ${3:map} = new HashMap<>();\n$0", "HashMap", "", "2_ds_002", "hashmap map"),
    snippet("TreeMap<>", "Map<${1:K}, ${2:V}> ${3:map} = new TreeMap<>();\n$0", "TreeMap", "Sorted by key", "2_ds_003", "treemap map sorted"),

    snippet("HashSet<>", "Set<${1:T}> ${2:set} = new HashSet<>();\n$0", "HashSet", "", "2_ds_010", "hashset set"),
    snippet("TreeSet<>", "Set<${1:T}> ${2:set} = new TreeSet<>();\n$0", "TreeSet", "Sorted set", "2_ds_011", "treeset set sorted"),

    snippet("ArrayDeque<> (stack/queue)", "Deque<${1:T}> ${2:dq} = new ArrayDeque<>();\n$0", "ArrayDeque", "Preferred for stack/queue/deque", "2_ds_020", "deque arraydeque"),
    snippet("PriorityQueue (min-heap)", "PriorityQueue<${1:T}> ${2:pq} = new PriorityQueue<>();\n$0", "Min-heap", "", "2_ds_030", "priorityqueue pq minheap"),
    snippet("PriorityQueue (max-heap)", "PriorityQueue<${1:T}> ${2:pq} = new PriorityQueue<>(Collections.reverseOrder());\n$0", "Max-heap", "", "2_ds_031", "priorityqueue pq maxheap"),

    snippet("int[][] grid", "int[][] ${1:grid} = new int[${2:r}][${3:c}];\n$0", "2D array", "", "2_ds_040", "int[][] grid"),
    snippet("adj list (unweighted)", "int n = ${1:n};\nList<Integer>[] g = new ArrayList[n];\nfor (int i = 0; i < n; i++) g[i] = new ArrayList<>();\n$0", "Adjacency list", "Unweighted graph", "2_ds_050", "adj list graph"),
    snippet("adj list (weighted int)", "int n = ${1:n};\nList<int[]>[] g = new ArrayList[n]; // edge: {to, w}\nfor (int i = 0; i < n; i++) g[i] = new ArrayList<>();\n$0", "Adjacency list", "Weighted graph ({to,w})", "2_ds_051", "adj list weighted graph"),
  ];

  // Utility / common library calls.
  const UTIL = [
    func("Arrays.sort", "Arrays.sort(${1:arr});", "Sort array", "Ascending", "3_util_001", "arrays sort"),
    func("Arrays.fill", "Arrays.fill(${1:arr}, ${2:value});", "Fill array", "", "3_util_002", "arrays fill"),
    func("Arrays.binarySearch", "Arrays.binarySearch(${1:arr}, ${2:key})", "Binary search", "returns index or -(insertionPoint)-1", "3_util_003", "binarySearch"),
    func("Arrays.copyOf", "Arrays.copyOf(${1:arr}, ${2:newLen});", "Copy array", "", "3_util_004", "copyOf arrays"),
    func("Arrays.copyOfRange", "Arrays.copyOfRange(${1:arr}, ${2:l}, ${3:r});", "Slice", "[l, r)", "3_util_005", "copyOfRange slice"),
    func("Arrays.toString", "Arrays.toString(${1:arr})", "Stringify 1D", "", "3_util_006", "toString arrays"),
    func("Arrays.deepToString", "Arrays.deepToString(${1:arr})", "Stringify nested", "", "3_util_007", "deepToString arrays"),

    func("Collections.sort", "Collections.sort(${1:list});", "Sort list", "", "3_util_010", "collections sort"),
    func("Collections.reverse", "Collections.reverse(${1:list});", "Reverse list", "", "3_util_011", "collections reverse"),
    func("Collections.frequency", "Collections.frequency(${1:collection}, ${2:obj})", "Frequency", "", "3_util_012", "frequency collections"),

    func("Math.min", "Math.min(${1:a}, ${2:b})", "Min", "", "3_util_020", "math min"),
    func("Math.max", "Math.max(${1:a}, ${2:b})", "Max", "", "3_util_021", "math max"),
    func("Math.abs", "Math.abs(${1:x})", "Abs", "", "3_util_022", "math abs"),
    func("Math.floorDiv", "Math.floorDiv(${1:a}, ${2:b})", "floorDiv", "handles negatives safely", "3_util_023", "floorDiv"),
    func("Math.floorMod", "Math.floorMod(${1:a}, ${2:b})", "floorMod", "handles negatives safely", "3_util_024", "floorMod"),

    snippet("String to char[]", "char[] ch = ${1:s}.toCharArray();\n$0", "toCharArray", "", "3_util_030", "toCharArray char[]"),
    snippet("parse int", "int x = Integer.parseInt(${1:s});\n$0", "parseInt", "", "3_util_040", "parseInt integer"),
    snippet("parse long", "long x = Long.parseLong(${1:s});\n$0", "parseLong", "", "3_util_041", "parseLong long"),

    snippet("freq++ (getOrDefault)", "${1:freq}.put(${2:key}, ${1:freq}.getOrDefault(${2:key}, 0) + 1);\n$0", "Increment freq", "Map.getOrDefault", "3_util_050", "getOrDefault freq"),
    snippet("freq++ (merge)", "${1:freq}.merge(${2:key}, 1, Integer::sum);\n$0", "Increment freq", "Map.merge", "3_util_051", "merge freq"),

    snippet("Comparator.comparingInt", "Comparator.comparingInt(${1:x} -> ${2:x.${3:field}})", "Comparator", "Sort by int key", "3_util_060", "comparingInt comparator"),
    snippet("sort map entries by value desc",
      "List<Map.Entry<${1:K}, Integer>> entries = new ArrayList<>(${2:map}.entrySet());\nentries.sort((a,b) -> Integer.compare(b.getValue(), a.getValue()));\n$0",
      "Sort entries",
      "Common for top-k problems",
      "3_util_061",
      "entryset sort value"
    ),

    // Regex (useful sometimes)
    snippet("Pattern/Matcher", "Pattern p = Pattern.compile(${1:\"regex\"});\nMatcher m = p.matcher(${2:s});\nwhile (m.find()) {\n    ${3:// use m.group()}\n}\n$0", "Regex", "", "3_util_070", "pattern matcher regex"),

    // BigInteger / BigDecimal (edge cases)
    snippet("BigInteger add/multiply", "BigInteger a = new BigInteger(${1:\"0\"});\nBigInteger b = new BigInteger(${2:\"0\"});\nBigInteger sum = a.add(b);\nBigInteger prod = a.multiply(b);\n$0", "BigInteger", "", "3_util_080", "biginteger"),
    snippet("BigDecimal rounding", "BigDecimal x = new BigDecimal(${1:\"0\"});\nBigDecimal y = x.setScale(${2:2}, RoundingMode.HALF_UP);\n$0", "BigDecimal", "Rounding", "3_util_081", "bigdecimal rounding"),
  ];

  // Streams (sometimes useful; often overkill—still handy for some users)
  const STREAMS = [
    snippet("IntStream.range", "IntStream.range(${1:0}, ${2:n}).forEach(i -> {\n    $0\n});", "Streams", "Range loop", "4_stream_001", "intstream range"),
    snippet("Arrays.stream(int[])", "int sum = Arrays.stream(${1:arr}).sum();\n$0", "Streams", "Sum ints", "4_stream_002", "arrays stream sum"),
    snippet("Collectors.toList", "List<${1:T}> list = ${2:stream}.collect(Collectors.toList());\n$0", "Streams", "", "4_stream_003", "collectors tolist"),
    snippet("groupingBy + counting",
      "Map<${1:K}, Long> cnt = ${2:stream}.collect(Collectors.groupingBy(${3:x -> x}, Collectors.counting()));\n$0",
      "Streams",
      "Frequency with groupingBy/counting",
      "4_stream_004",
      "groupingBy counting"
    ),
  ];

  // Fast IO snippets (online judge friendly).
  const IO = [
    snippet(
      "BufferedReader + StringTokenizer",
      "BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\nStringTokenizer st = new StringTokenizer(br.readLine());\n$0",
      "Classic input",
      "",
      "5_io_001",
      "bufferedreader stringtokenizer"
    ),
    snippet(
      "FastScanner (BufferedInputStream)",
`static class FastScanner {
    private final InputStream in;
    private final byte[] buffer = new byte[1 << 16];
    private int ptr = 0, len = 0;

    FastScanner(InputStream is) { this.in = is; }

    private int readByte() throws IOException {
        if (ptr >= len) {
            len = in.read(buffer);
            ptr = 0;
            if (len <= 0) return -1;
        }
        return buffer[ptr++];
    }

    String next() throws IOException {
        StringBuilder sb = new StringBuilder();
        int c;
        while ((c = readByte()) != -1 && c <= ' ') {}
        if (c == -1) return null;
        do {
            sb.append((char)c);
            c = readByte();
        } while (c > ' ');
        return sb.toString();
    }

    int nextInt() throws IOException {
        int c;
        while ((c = readByte()) != -1 && c <= ' ') {}
        int sign = 1;
        if (c == '-') { sign = -1; c = readByte(); }
        int val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readByte();
        }
        return val * sign;
    }

    long nextLong() throws IOException {
        int c;
        while ((c = readByte()) != -1 && c <= ' ') {}
        int sign = 1;
        if (c == '-') { sign = -1; c = readByte(); }
        long val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readByte();
        }
        return val * sign;
    }
}

$0`,
      "Fast input",
      "Much faster than Scanner",
      "5_io_010",
      "fastscanner fast input"
    ),
    snippet(
      "Read int[] (n then n ints)",
      "int n = ${1:fs}.nextInt();\nint[] a = new int[n];\nfor (int i = 0; i < n; i++) a[i] = ${1:fs}.nextInt();\n$0",
      "Read int[]",
      "",
      "5_io_020",
      "read array ints"
    ),
    snippet(
      "Print int[] (space-separated)",
      "StringBuilder sb = new StringBuilder();\nfor (int i = 0; i < ${1:arr}.length; i++) {\n    if (i > 0) sb.append(' ');\n    sb.append(${1:arr}[i]);\n}\nSystem.out.println(sb.toString());\n$0",
      "Print int[]",
      "",
      "5_io_030",
      "print array output"
    ),
  ];

  // Algorithm templates (fill-in-the-blanks; not full solutions).
  const ALGO = [
    snippet(
      "binary search (lower_bound)",
      "int lo = 0, hi = ${1:arr}.length; // [lo, hi)\nwhile (lo < hi) {\n    int mid = lo + (hi - lo) / 2;\n    if (${1:arr}[mid] < ${2:target}) lo = mid + 1;\n    else hi = mid;\n}\n// lo = first index with arr[lo] >= target\n$0",
      "Binary search",
      "Lower bound template",
      "6_algo_001",
      "binary search lower_bound"
    ),
    snippet(
      "two pointers",
      "int l = 0, r = ${1:arr}.length - 1;\nwhile (l < r) {\n    if (${2:condition}) {\n        l++;\n    } else {\n        r--;\n    }\n}\n$0",
      "Two pointers",
      "",
      "6_algo_010",
      "two pointers"
    ),
    snippet(
      "sliding window",
      "int l = 0;\nfor (int r = 0; r < ${1:arr}.length; r++) {\n    ${2:// add arr[r] to state}\n    while (${3:tooBig}) {\n        ${4:// remove arr[l] from state}\n        l++;\n    }\n    ${5:// update answer}\n}\n$0",
      "Sliding window",
      "",
      "6_algo_020",
      "sliding window"
    ),
    snippet(
      "prefix sums (1D)",
      "int n = ${1:arr}.length;\nlong[] pref = new long[n + 1];\nfor (int i = 0; i < n; i++) pref[i + 1] = pref[i] + ${1:arr}[i];\n// sum [l, r) = pref[r] - pref[l]\n$0",
      "Prefix sums",
      "",
      "6_algo_030",
      "prefix sum"
    ),
    snippet(
      "DFS (recursive)",
`void dfs(int u, List<Integer>[] g, boolean[] vis) {
    vis[u] = true;
    for (int v : g[u]) {
        if (!vis[v]) dfs(v, g, vis);
    }
}

$0`,
      "DFS",
      "Graph traversal",
      "6_algo_040",
      "dfs recursion"
    ),
    snippet(
      "BFS (queue)",
      "Deque<Integer> q = new ArrayDeque<>();\nboolean[] vis = new boolean[${1:n}];\nq.add(${2:start});\nvis[${2:start}] = true;\nwhile (!q.isEmpty()) {\n    int u = q.poll();\n    ${3:// process u}\n    for (int v : ${4:g}[u]) {\n        if (!vis[v]) {\n            vis[v] = true;\n            q.add(v);\n        }\n    }\n}\n$0",
      "BFS",
      "Queue-based traversal",
      "6_algo_041",
      "bfs queue"
    ),
    snippet(
      "BFS on grid (4-dir)",
      "int R = ${1:R}, C = ${2:C};\nint[] dr = {-1, 1, 0, 0};\nint[] dc = {0, 0, -1, 1};\nDeque<int[]> q = new ArrayDeque<>();\nboolean[][] vis = new boolean[R][C];\nq.add(new int[]{${3:sr}, ${4:sc}});\nvis[${3:sr}][${4:sc}] = true;\nwhile (!q.isEmpty()) {\n    int[] cur = q.poll();\n    int r = cur[0], c = cur[1];\n    ${5:// process (r,c)}\n    for (int k = 0; k < 4; k++) {\n        int nr = r + dr[k], nc = c + dc[k];\n        if (nr < 0 || nr >= R || nc < 0 || nc >= C) continue;\n        if (vis[nr][nc]) continue;\n        if (${6:false}) continue; // replace false with your isBlocked(nr,nc) condition\n        vis[nr][nc] = true;\n        q.add(new int[]{nr, nc});\n    }\n}\n$0",
      "Grid BFS",
      "",
      "6_algo_042",
      "grid bfs"
    ),
    snippet(
      "topological sort (Kahn)",
      "int n = ${1:n};\nList<Integer>[] g = new ArrayList[n];\nfor (int i = 0; i < n; i++) g[i] = new ArrayList<>();\nint[] indeg = new int[n];\n${2:// build g + indeg}\nDeque<Integer> q = new ArrayDeque<>();\nfor (int i = 0; i < n; i++) if (indeg[i] == 0) q.add(i);\nList<Integer> order = new ArrayList<>();\nwhile (!q.isEmpty()) {\n    int u = q.poll();\n    order.add(u);\n    for (int v : g[u]) {\n        if (--indeg[v] == 0) q.add(v);\n    }\n}\n// if (order.size() < n) => cycle\n$0",
      "Topo sort",
      "",
      "6_algo_050",
      "toposort kahn"
    ),
    snippet(
      "Dijkstra (weighted graph)",
      "int n = ${1:n};\nList<int[]>[] g = new ArrayList[n]; // edge: {to, w}\nfor (int i = 0; i < n; i++) g[i] = new ArrayList<>();\n${2:// add edges: g[u].add(new int[]{v, w});}\nlong[] dist = new long[n];\nArrays.fill(dist, Long.MAX_VALUE);\ndist[${3:src}] = 0;\nPriorityQueue<long[]> pq = new PriorityQueue<>(Comparator.comparingLong(a -> a[0])); // {d, node}\npq.add(new long[]{0, ${3:src}});\nwhile (!pq.isEmpty()) {\n    long[] cur = pq.poll();\n    long d = cur[0];\n    int u = (int) cur[1];\n    if (d != dist[u]) continue;\n    for (int[] e : g[u]) {\n        int v = e[0];\n        long w = e[1];\n        if (dist[u] != Long.MAX_VALUE && dist[u] + w < dist[v]) {\n            dist[v] = dist[u] + w;\n            pq.add(new long[]{dist[v], v});\n        }\n    }\n}\n$0",
      "Dijkstra",
      "",
      "6_algo_060",
      "dijkstra shortest path"
    ),
    snippet(
      "Union-Find (DSU)",
`static class DSU {
    int[] p, r;
    DSU(int n) {
        p = new int[n]; r = new int[n];
        for (int i = 0; i < n; i++) p[i] = i;
    }
    int find(int x) {
        if (p[x] != x) p[x] = find(p[x]);
        return p[x];
    }
    boolean union(int a, int b) {
        a = find(a); b = find(b);
        if (a == b) return false;
        if (r[a] < r[b]) { int t = a; a = b; b = t; }
        p[b] = a;
        if (r[a] == r[b]) r[a]++;
        return true;
    }
}

$0`,
      "DSU",
      "",
      "6_algo_070",
      "union find dsu"
    ),
    snippet(
      "gcd / lcm",
`static long gcd(long a, long b) {
    while (b != 0) {
        long t = a % b;
        a = b; b = t;
    }
    return Math.abs(a);
}

static long lcm(long a, long b) {
    return a / gcd(a, b) * b;
}

$0`,
      "gcd/lcm",
      "",
      "6_algo_080",
      "gcd lcm"
    ),
    snippet(
      "modPow",
`static long modPow(long a, long e, long mod) {
    long res = 1 % mod;
    a %= mod;
    while (e > 0) {
        if ((e & 1) == 1) res = (res * a) % mod;
        a = (a * a) % mod;
        e >>= 1;
    }
    return res;
}

$0`,
      "modPow",
      "Binary exponentiation",
      "6_algo_081",
      "modpow powmod"
    ),
    snippet(
      "monotonic stack (indices)",
      "Deque<Integer> st = new ArrayDeque<>();\nfor (int i = 0; i < ${1:arr}.length; i++) {\n    while (!st.isEmpty() && ${1:arr}[st.peek()] <= ${1:arr}[i]) {\n        st.pop();\n    }\n    // st.peek() is previous greater index (or none)\n    st.push(i);\n}\n$0",
      "Monotonic stack",
      "",
      "6_algo_100",
      "monotonic stack"
    ),
  ];

  // Optional "system-ish" APIs (many sandboxes disallow these).
  const SYSTEM = [
    // Process
    snippet("ProcessBuilder", "new ProcessBuilder(${1:command}).start();\n$0", "Start process", "Often disallowed in sandboxes", "7_sys_001", "processbuilder process"),
    // Files (NIO)
    snippet("Files.readString", "String s = Files.readString(Path.of(${1:\"file.txt\"}));\n$0", "Read file", "Java 11+", "7_sys_010", "files readString path"),
    snippet("Files.writeString", "Files.writeString(Path.of(${1:\"file.txt\"}), ${2:content});\n$0", "Write file", "Java 11+", "7_sys_011", "files writeString path"),
    snippet("Files.readAllBytes", "byte[] data = Files.readAllBytes(Path.of(${1:\"file.bin\"}));\n$0", "Read bytes", "", "7_sys_012", "files readAllBytes"),
    snippet("Files.copy", "Files.copy(${1:source}, ${2:target}, StandardCopyOption.REPLACE_EXISTING);\n$0", "Copy file", "", "7_sys_013", "files copy"),
    snippet("Files.move", "Files.move(${1:source}, ${2:target});\n$0", "Move file", "", "7_sys_014", "files move"),
    snippet("Files.delete", "Files.delete(${1:path});\n$0", "Delete file", "", "7_sys_015", "files delete"),
    // Networking
    snippet("new URL", "URL url = new URL(${1:\"https://example.com\"});\n$0", "URL", "", "7_sys_020", "url new url"),
    snippet("HttpURLConnection", "HttpURLConnection conn = (HttpURLConnection) new URL(${1:\"https://example.com\"}).openConnection();\nconn.setRequestMethod(${2:\"GET\"});\nint code = conn.getResponseCode();\n$0", "HTTP", "HttpURLConnection", "7_sys_021", "http urlconnection"),
    snippet("new Socket", "Socket s = new Socket(${1:\"host\"}, ${2:port});\n$0", "Socket", "", "7_sys_022", "socket"),
    snippet("new ServerSocket", "ServerSocket ss = new ServerSocket(${1:port});\nSocket s = ss.accept();\n$0", "ServerSocket", "", "7_sys_023", "serversocket"),
  ];

  // Dot-trigger suggestions (contextual).
  // We don't have type info without a Java LSP, so we do:
  // 1) qualifier-based lists for common static classes (Arrays., Collections., Math., System.out., etc.)
  // 2) name-heuristics for common variable naming patterns (sb., pq., map., set., list., dq./q.)
  //
  // Keep these lists short-ish to avoid overwhelming the UI.

  const DOT_GENERIC = [
    // String / array-ish
    func("length", "length", "Array.length", "", "0_dot_000", "length"),
    func("length()", "length()", "String.length", "", "0_dot_001", "length"),
    func("charAt(i)", "charAt(${1:i})", "String.charAt", "", "0_dot_002", "charAt"),
    func("substring(i)", "substring(${1:i})", "String.substring", "", "0_dot_003", "substring"),
    func("substring(i, j)", "substring(${1:i}, ${2:j})", "String.substring", "", "0_dot_004", "substring"),
    func("indexOf(x)", "indexOf(${1:x})", "String/List indexOf", "", "0_dot_005", "indexOf"),
    func("lastIndexOf(x)", "lastIndexOf(${1:x})", "String/List lastIndexOf", "", "0_dot_006", "lastIndexOf"),
    func("startsWith(prefix)", "startsWith(${1:prefix})", "String.startsWith", "", "0_dot_007", "startsWith"),
    func("endsWith(suffix)", "endsWith(${1:suffix})", "String.endsWith", "", "0_dot_008", "endsWith"),
    func("split(regex)", "split(${1:\"\\\\s+\"})", "String.split", "", "0_dot_009", "split"),
    func("trim()", "trim()", "String.trim", "", "0_dot_010", "trim"),
    func("toLowerCase()", "toLowerCase()", "String.toLowerCase", "", "0_dot_011", "toLowerCase"),
    func("toUpperCase()", "toUpperCase()", "String.toUpperCase", "", "0_dot_012", "toUpperCase"),
    func("replace(a,b)", "replace(${1:oldCharOrSeq}, ${2:newCharOrSeq})", "String.replace", "", "0_dot_013", "replace"),
    func("replaceAll(r, repl)", "replaceAll(${1:\"regex\"}, ${2:\"repl\"})", "String.replaceAll", "", "0_dot_014", "replaceAll"),
    func("equalsIgnoreCase(s)", "equalsIgnoreCase(${1:s})", "String.equalsIgnoreCase", "", "0_dot_015", "equalsIgnoreCase"),

    // Collections / maps / queues
    func("size()", "size()", "Size", "List/Set/Map/etc.", "0_dot_100", "size"),
    func("isEmpty()", "isEmpty()", "Empty?", "", "0_dot_101", "isEmpty"),
    func("clear()", "clear()", "Clear", "", "0_dot_102", "clear"),
    func("add(x)", "add(${1:x})", "Add", "", "0_dot_103", "add"),
    func("addAll(xs)", "addAll(${1:xs})", "Add all", "", "0_dot_104", "addAll"),
    func("remove(x)", "remove(${1:x})", "Remove", "", "0_dot_105", "remove"),
    func("removeIf(p)", "removeIf(${1:x -> true})", "Remove if", "", "0_dot_106", "removeIf"),
    func("contains(x)", "contains(${1:x})", "Contains", "", "0_dot_107", "contains"),
    func("get(i)", "get(${1:i})", "Get", "", "0_dot_108", "get"),
    func("set(i,x)", "set(${1:i}, ${2:x})", "Set", "", "0_dot_109", "set"),
    func("offer(x)", "offer(${1:x})", "Queue.offer", "", "0_dot_110", "offer"),
    func("poll()", "poll()", "Queue.poll", "", "0_dot_111", "poll"),
    func("peek()", "peek()", "Queue.peek", "", "0_dot_112", "peek"),
    func("push(x)", "push(${1:x})", "Deque.push", "", "0_dot_113", "push"),
    func("pop()", "pop()", "Deque.pop", "", "0_dot_114", "pop"),
    func("put(k,v)", "put(${1:k}, ${2:v})", "Map.put", "", "0_dot_115", "put"),
    func("getOrDefault(k,d)", "getOrDefault(${1:k}, ${2:d})", "Map.getOrDefault", "", "0_dot_116", "getOrDefault"),
    func("containsKey(k)", "containsKey(${1:k})", "Map.containsKey", "", "0_dot_117", "containsKey"),
    func("keySet()", "keySet()", "Map.keySet", "", "0_dot_118", "keySet"),
    func("values()", "values()", "Map.values", "", "0_dot_119", "values"),
    func("entrySet()", "entrySet()", "Map.entrySet", "", "0_dot_120", "entrySet"),
    func("stream()", "stream()", "Stream", "", "0_dot_121", "stream"),
    func("toString()", "toString()", "toString", "", "0_dot_122", "toString"),
  ];

  const DOT_Arrays = [
    func("sort(a)", "sort(${1:a})", "Arrays.sort", "", "0_dotA_001", "sort"),
    func("fill(a, v)", "fill(${1:a}, ${2:v})", "Arrays.fill", "", "0_dotA_002", "fill"),
    func("binarySearch(a, key)", "binarySearch(${1:a}, ${2:key})", "Arrays.binarySearch", "", "0_dotA_003", "binarySearch"),
    func("copyOf(a, n)", "copyOf(${1:a}, ${2:n})", "Arrays.copyOf", "", "0_dotA_004", "copyOf"),
    func("copyOfRange(a, l, r)", "copyOfRange(${1:a}, ${2:l}, ${3:r})", "Arrays.copyOfRange", "", "0_dotA_005", "copyOfRange"),
    func("toString(a)", "toString(${1:a})", "Arrays.toString", "", "0_dotA_006", "toString"),
    func("deepToString(a)", "deepToString(${1:a})", "Arrays.deepToString", "", "0_dotA_007", "deepToString"),
    func("stream(a)", "stream(${1:a})", "Arrays.stream", "", "0_dotA_008", "stream"),
  ];

  const DOT_Collections = [
    func("sort(list)", "sort(${1:list})", "Collections.sort", "", "0_dotC_001", "sort"),
    func("reverse(list)", "reverse(${1:list})", "Collections.reverse", "", "0_dotC_002", "reverse"),
    func("shuffle(list)", "shuffle(${1:list})", "Collections.shuffle", "", "0_dotC_003", "shuffle"),
    func("min(coll)", "min(${1:coll})", "Collections.min", "", "0_dotC_004", "min"),
    func("max(coll)", "max(${1:coll})", "Collections.max", "", "0_dotC_005", "max"),
    func("frequency(coll, x)", "frequency(${1:coll}, ${2:x})", "Collections.frequency", "", "0_dotC_006", "frequency"),
    func("singletonList(x)", "singletonList(${1:x})", "Collections.singletonList", "", "0_dotC_007", "singletonList"),
    func("emptyList()", "emptyList()", "Collections.emptyList", "", "0_dotC_008", "emptyList"),
    func("emptyMap()", "emptyMap()", "Collections.emptyMap", "", "0_dotC_009", "emptyMap"),
  ];

  const DOT_Math = [
    func("min(a,b)", "min(${1:a}, ${2:b})", "Math.min", "", "0_dotM_001", "min"),
    func("max(a,b)", "max(${1:a}, ${2:b})", "Math.max", "", "0_dotM_002", "max"),
    func("abs(x)", "abs(${1:x})", "Math.abs", "", "0_dotM_003", "abs"),
    func("sqrt(x)", "sqrt(${1:x})", "Math.sqrt", "", "0_dotM_004", "sqrt"),
    func("pow(a,b)", "pow(${1:a}, ${2:b})", "Math.pow", "", "0_dotM_005", "pow"),
    func("floor(x)", "floor(${1:x})", "Math.floor", "", "0_dotM_006", "floor"),
    func("ceil(x)", "ceil(${1:x})", "Math.ceil", "", "0_dotM_007", "ceil"),
    func("round(x)", "round(${1:x})", "Math.round", "", "0_dotM_008", "round"),
  ];

  const DOT_System = [
    func("currentTimeMillis()", "currentTimeMillis()", "System time", "", "0_dotS_001", "currentTimeMillis"),
    func("nanoTime()", "nanoTime()", "System time", "", "0_dotS_002", "nanoTime"),
    func("getenv()", "getenv(${1:\"VAR\"})", "Env var", "", "0_dotS_003", "getenv"),
    func("getProperty()", "getProperty(${1:\"key\"})", "Property", "", "0_dotS_004", "getProperty"),
  ];

  const DOT_SystemOut = [
    func("print(x)", "print(${1:x})", "Print", "", "0_dotSO_001", "print"),
    func("println(x)", "println(${1:x})", "Println", "", "0_dotSO_002", "println"),
    func("printf(fmt, ...)", "printf(${1:\"%s\\n\"}, ${2:args})", "printf", "", "0_dotSO_003", "printf"),
    func("format(fmt, ...)", "format(${1:\"%s\\n\"}, ${2:args})", "format", "", "0_dotSO_004", "format"),
    func("flush()", "flush()", "flush", "", "0_dotSO_005", "flush"),
  ];

  const DOT_SystemErr = [
    func("println(x)", "println(${1:x})", "stderr println", "", "0_dotSE_001", "println"),
    func("print(x)", "print(${1:x})", "stderr print", "", "0_dotSE_002", "print"),
    func("printf(fmt, ...)", "printf(${1:\"%s\\n\"}, ${2:args})", "stderr printf", "", "0_dotSE_003", "printf"),
    func("flush()", "flush()", "stderr flush", "", "0_dotSE_004", "flush"),
  ];

  const DOT_StringStatic = [
    func("valueOf(x)", "valueOf(${1:x})", "String.valueOf", "", "0_dotStr_001", "valueOf"),
    func("format(fmt,...)", "format(${1:\"%s\"}, ${2:args})", "String.format", "", "0_dotStr_002", "format"),
    func("join(delim, ...)", "join(${1:\",\"}, ${2:parts})", "String.join", "", "0_dotStr_003", "join"),
  ];

  const DOT_IntegerStatic = [
    func("parseInt(s)", "parseInt(${1:s})", "Integer.parseInt", "", "0_dotI_001", "parseInt"),
    func("toString(x)", "toString(${1:x})", "Integer.toString", "", "0_dotI_002", "toString"),
    func("compare(a,b)", "compare(${1:a}, ${2:b})", "Integer.compare", "", "0_dotI_003", "compare"),
    func("max(a,b)", "max(${1:a}, ${2:b})", "Integer.max", "", "0_dotI_004", "max"),
    func("min(a,b)", "min(${1:a}, ${2:b})", "Integer.min", "", "0_dotI_005", "min"),
  ];

  const DOT_LongStatic = [
    func("parseLong(s)", "parseLong(${1:s})", "Long.parseLong", "", "0_dotL_001", "parseLong"),
    func("toString(x)", "toString(${1:x})", "Long.toString", "", "0_dotL_002", "toString"),
    func("compare(a,b)", "compare(${1:a}, ${2:b})", "Long.compare", "", "0_dotL_003", "compare"),
    func("max(a,b)", "max(${1:a}, ${2:b})", "Long.max", "", "0_dotL_004", "max"),
    func("min(a,b)", "min(${1:a}, ${2:b})", "Long.min", "", "0_dotL_005", "min"),
  ];

  const DOT_Objects = [
    func("requireNonNull(x)", "requireNonNull(${1:x})", "Objects.requireNonNull", "", "0_dotO_001", "requireNonNull"),
    func("equals(a,b)", "equals(${1:a}, ${2:b})", "Objects.equals", "", "0_dotO_002", "equals"),
    func("hash(...)", "hash(${1:args})", "Objects.hash", "", "0_dotO_003", "hash"),
    func("toString(x)", "toString(${1:x})", "Objects.toString", "", "0_dotO_004", "toString"),
  ];

  const DOT_Optional = [
    func("of(x)", "of(${1:x})", "Optional.of", "", "0_dotOpt_001", "of"),
    func("ofNullable(x)", "ofNullable(${1:x})", "Optional.ofNullable", "", "0_dotOpt_002", "ofNullable"),
    func("empty()", "empty()", "Optional.empty", "", "0_dotOpt_003", "empty"),
  ];

  const DOT_StringBuilder = [
    func("append(x)", "append(${1:x})", "StringBuilder.append", "", "0_dotSB_001", "append"),
    func("setLength(n)", "setLength(${1:n})", "StringBuilder.setLength", "", "0_dotSB_002", "setLength"),
    func("reverse()", "reverse()", "StringBuilder.reverse", "", "0_dotSB_003", "reverse"),
    func("toString()", "toString()", "StringBuilder.toString", "", "0_dotSB_004", "toString"),
  ];

  const DOT_Map = [
    func("get(k)", "get(${1:k})", "Map.get", "", "0_dotMap_001", "get"),
    func("put(k,v)", "put(${1:k}, ${2:v})", "Map.put", "", "0_dotMap_002", "put"),
    func("getOrDefault(k, d)", "getOrDefault(${1:k}, ${2:d})", "Map.getOrDefault", "", "0_dotMap_003", "getOrDefault"),
    func("containsKey(k)", "containsKey(${1:k})", "Map.containsKey", "", "0_dotMap_004", "containsKey"),
    func("remove(k)", "remove(${1:k})", "Map.remove", "", "0_dotMap_005", "remove"),
    func("computeIfAbsent(k, f)", "computeIfAbsent(${1:k}, ${2:key -> value})", "Map.computeIfAbsent", "", "0_dotMap_006", "computeIfAbsent"),
    func("merge(k, v, f)", "merge(${1:k}, ${2:v}, ${3:Integer::sum})", "Map.merge", "", "0_dotMap_007", "merge"),
    func("entrySet()", "entrySet()", "Map.entrySet", "", "0_dotMap_008", "entrySet"),
    func("keySet()", "keySet()", "Map.keySet", "", "0_dotMap_009", "keySet"),
    func("values()", "values()", "Map.values", "", "0_dotMap_010", "values"),
  ];

  const DOT_Set = [
    func("add(x)", "add(${1:x})", "Set.add", "", "0_dotSet_001", "add"),
    func("remove(x)", "remove(${1:x})", "Set.remove", "", "0_dotSet_002", "remove"),
    func("contains(x)", "contains(${1:x})", "Set.contains", "", "0_dotSet_003", "contains"),
    func("size()", "size()", "Set.size", "", "0_dotSet_004", "size"),
    func("isEmpty()", "isEmpty()", "Set.isEmpty", "", "0_dotSet_005", "isEmpty"),
  ];

  const DOT_List = [
    func("add(x)", "add(${1:x})", "List.add", "", "0_dotList_001", "add"),
    func("get(i)", "get(${1:i})", "List.get", "", "0_dotList_002", "get"),
    func("set(i,x)", "set(${1:i}, ${2:x})", "List.set", "", "0_dotList_003", "set"),
    func("size()", "size()", "List.size", "", "0_dotList_004", "size"),
    func("sort(cmp)", "sort(${1:cmp})", "List.sort", "", "0_dotList_005", "sort"),
  ];

  const DOT_Deque = [
    func("add(x)", "add(${1:x})", "Deque.add", "", "0_dotDQ_001", "add"),
    func("addFirst(x)", "addFirst(${1:x})", "Deque.addFirst", "", "0_dotDQ_002", "addFirst"),
    func("addLast(x)", "addLast(${1:x})", "Deque.addLast", "", "0_dotDQ_003", "addLast"),
    func("offer(x)", "offer(${1:x})", "Deque.offer", "", "0_dotDQ_004", "offer"),
    func("offerFirst(x)", "offerFirst(${1:x})", "Deque.offerFirst", "", "0_dotDQ_005", "offerFirst"),
    func("offerLast(x)", "offerLast(${1:x})", "Deque.offerLast", "", "0_dotDQ_006", "offerLast"),
    func("poll()", "poll()", "Deque.poll", "", "0_dotDQ_007", "poll"),
    func("pollFirst()", "pollFirst()", "Deque.pollFirst", "", "0_dotDQ_008", "pollFirst"),
    func("pollLast()", "pollLast()", "Deque.pollLast", "", "0_dotDQ_009", "pollLast"),
    func("peek()", "peek()", "Deque.peek", "", "0_dotDQ_010", "peek"),
    func("peekFirst()", "peekFirst()", "Deque.peekFirst", "", "0_dotDQ_011", "peekFirst"),
    func("peekLast()", "peekLast()", "Deque.peekLast", "", "0_dotDQ_012", "peekLast"),
    func("push(x)", "push(${1:x})", "Deque.push", "", "0_dotDQ_013", "push"),
    func("pop()", "pop()", "Deque.pop", "", "0_dotDQ_014", "pop"),
  ];

  const DOT_PriorityQueue = [
    func("add(x)", "add(${1:x})", "PQ add", "", "0_dotPQ_001", "add"),
    func("offer(x)", "offer(${1:x})", "PQ offer", "", "0_dotPQ_002", "offer"),
    func("poll()", "poll()", "PQ poll", "", "0_dotPQ_003", "poll"),
    func("peek()", "peek()", "PQ peek", "", "0_dotPQ_004", "peek"),
    func("size()", "size()", "PQ size", "", "0_dotPQ_005", "size"),
    func("isEmpty()", "isEmpty()", "PQ isEmpty", "", "0_dotPQ_006", "isEmpty"),
    func("clear()", "clear()", "PQ clear", "", "0_dotPQ_007", "clear"),
  ];

  const DOT_BY_QUALIFIER = {
    Arrays: DOT_Arrays,
    Collections: DOT_Collections,
    Math: DOT_Math,
    System: DOT_System,
    "System.out": DOT_SystemOut,
    "System.err": DOT_SystemErr,
    String: DOT_StringStatic,
    Integer: DOT_IntegerStatic,
    Long: DOT_LongStatic,
    Objects: DOT_Objects,
    Optional: DOT_Optional,
  };

  if (ENABLE_SYSTEM_APIS) {
    // Add extra qualifier lists if you want:
    // DOT_BY_QUALIFIER.Files = [...];
  }


  const ALL = [
    ...TOP,
    ...FLOW,
    ...DS,
    ...UTIL,
    ...STREAMS,
    ...IO,
    ...(ENABLE_SYSTEM_APIS ? SYSTEM : []),
    ...ALGO,
  ];

  // ---------------------- register ----------------------

  function registerJavaCompletions() {
    if (!window.monaco || !monaco.languages || !monaco.languages.registerCompletionItemProvider) {
      console.warn("Monaco not ready yet — call registerJavaCompletions() after Monaco loads.");
      return;
    }

    // Dispose old provider (hot reload / multiple page inits)
    if (window.__javaCompletionDisposable && typeof window.__javaCompletionDisposable.dispose === "function") {
      window.__javaCompletionDisposable.dispose();
    }

    window.__javaCompletionDisposable = monaco.languages.registerCompletionItemProvider("java", {
      triggerCharacters: [".", "("],
      provideCompletionItems: function (model, position) {
        const { word, range } = getWordAndRange(model, position);
        const prefix = lower(word);
        const linePrefix = getLinePrefix(model, position);
        const isDotContext = /\.\s*$/.test(linePrefix);

        let dotCatalog = DOT_GENERIC;
        if (isDotContext) {
          const m = linePrefix.match(/([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\.\s*$/);
          const qual = m ? m[1] : "";
          if (qual && DOT_BY_QUALIFIER[qual]) {
            dotCatalog = DOT_BY_QUALIFIER[qual];
          } else if (qual) {
            const ql = lower(qual);
            if (/(^|[^a-z0-9])sb$/.test(" " + ql)) dotCatalog = DOT_StringBuilder;
            else if (/(^|[^a-z0-9])pq$/.test(" " + ql)) dotCatalog = DOT_PriorityQueue;
            else if (/(dq|deque|queue|^q$|q$)/.test(ql)) dotCatalog = DOT_Deque;
            else if (/map$/.test(ql)) dotCatalog = DOT_Map;
            else if (/(set|seen)$/.test(ql)) dotCatalog = DOT_Set;
            else if (/(list|lists|arr|nums|values)$/.test(ql)) dotCatalog = DOT_List;
          }
        }

        const catalog = isDotContext ? dotCatalog : ALL;

        // small, high-signal default list when prefix is empty
        let metas;
        if (!isDotContext && prefix.length === 0) {
          metas = [...TOP, ...FLOW.slice(0, 6), ...DS.slice(0, 6)];
        } else {
          metas = catalog.filter((m) => lower(m.filterText || m.label).includes(prefix));
          if (!metas.length) metas = catalog;
        }

        return { suggestions: asSuggestions(metas, range) };
      },
    });

    return window.__javaCompletionDisposable;
  }

  window.registerJavaCompletions = registerJavaCompletions;
})();
