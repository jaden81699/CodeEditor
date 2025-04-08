// javaCompletions.js

// Function to register custom completions for Java
function registerJavaCompletions() {
    monaco.languages.registerCompletionItemProvider('java', {
        triggerCharacters: ['.', '('],
        provideCompletionItems: function (model, position) {
            const suggestions = [
                {
                    label: "System.out.println",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'System.out.println(${1:message});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Prints a message to the console.'
                },
                {
                    label: "System.err.println",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'System.err.println(${1:message});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Prints an error message to the console.'
                },
                {
                    label: "main method",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'public static void main(String[] args) {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'The entry point of a Java application.'
                },
                {
                    label: "for loop",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'for (int ${1:i} = 0; ${1:i} < ${2:n}; ${1:i}++) {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Standard for loop.'
                },
                {
                    label: "while loop",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'while (${1:condition}) {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'While loop.'
                },
                {
                    label: "do while loop",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'do {\n\t$0\n} while (${1:condition});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Do-while loop.'
                },
                {
                    label: "if statement",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'if (${1:condition}) {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Simple if statement.'
                },
                {
                    label: "else statement",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'else {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Else clause.'
                },
                {
                    label: "else if statement",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'else if (${1:condition}) {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Else-if clause.'
                },
                {
                    label: "switch statement",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'switch (${1:variable}) {\n\tcase ${2:constant}:\n\t\t$0\n\t\tbreak;\n\tdefault:\n\t\tbreak;\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Switch statement.'
                },
                {
                    label: "try catch",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'try {\n\t$0\n} catch (${1:Exception} e) {\n\t$2\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Try-catch block.'
                },
                {
                    label: "try catch finally",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'try {\n\t$0\n} catch (${1:Exception} e) {\n\t$2\n} finally {\n\t$3\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Try-catch-finally block.'
                },
                {
                    label: "synchronized block",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'synchronized(${1:object}) {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Synchronized block.'
                },
                {
                    label: "class definition",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'public class ${1:ClassName} {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Define a new class.'
                },
                {
                    label: "interface definition",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'public interface ${1:InterfaceName} {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Define a new interface.'
                },
                {
                    label: "enum definition",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'public enum ${1:EnumName} {\n\t${2:CONSTANT1}, ${3:CONSTANT2};\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Define a new enum.'
                },
                {
                    label: "import statement",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'import ${1:package.name};',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Import a package.'
                },
                {
                    label: "package declaration",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'package ${1:package.name};',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Declare a package.'
                },
                {
                    label: "public keyword",
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'public',
                    documentation: 'Public access modifier.'
                },
                {
                    label: "private keyword",
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'private',
                    documentation: 'Private access modifier.'
                },
                {
                    label: "protected keyword",
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'protected',
                    documentation: 'Protected access modifier.'
                },
                {
                    label: "static keyword",
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'static',
                    documentation: 'Static modifier.'
                },
                {
                    label: "final keyword",
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'final',
                    documentation: 'Final modifier.'
                },
                {
                    label: "abstract keyword",
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'abstract',
                    documentation: 'Abstract modifier.'
                },
                {
                    label: "implements",
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'implements',
                    documentation: 'Implements keyword for interfaces.'
                },
                {
                    label: "extends",
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'extends',
                    documentation: 'Extends keyword for inheritance.'
                },
                {
                    label: "this keyword",
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'this',
                    documentation: 'Current instance reference.'
                },
                {
                    label: "super keyword",
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'super',
                    documentation: 'Reference to parent class.'
                },
                {
                    label: "new keyword",
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'new',
                    documentation: 'Creates a new instance.'
                },
                {
                    label: "return statement",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'return $0;',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Return from a method.'
                },
                {
                    label: "ArrayList initialization",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'List<${1:Type}> ${2:list} = new ArrayList<>();',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create an ArrayList.'
                },
                {
                    label: "HashMap initialization",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Map<${1:Key}, ${2:Value}> ${3:map} = new HashMap<>();',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a HashMap.'
                },
                {
                    label: "LinkedList initialization",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'List<${1:Type}> ${2:list} = new LinkedList<>();',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a LinkedList.'
                },
                {
                    label: "HashSet initialization",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Set<${1:Type}> ${2:set} = new HashSet<>();',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a HashSet.'
                },
                {
                    label: "TreeMap initialization",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Map<${1:Key}, ${2:Value}> ${3:map} = new TreeMap<>();',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a TreeMap.'
                },
                {
                    label: "for-each loop (collection)",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'for (${1:Type} ${2:item} : ${3:collection}) {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Iterate over a collection.'
                },
                {
                    label: "Iterator loop",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'for (Iterator<${1:Type}> iterator = ${2:collection}.iterator(); iterator.hasNext();) {\n\t${1:Type} ${3:element} = iterator.next();\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Iterate using an Iterator.'
                },
                {
                    label: "try-with-resources",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'try (${1:Resource} ${2:resource} = ${3:createResource}()) {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Try with resources for AutoCloseable objects.'
                },
                {
                    label: "StringBuilder initialization",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'StringBuilder ${1:sb} = new StringBuilder();',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Initialize a StringBuilder.'
                },
                {
                    label: "StringBuffer initialization",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'StringBuffer ${1:sb} = new StringBuffer();',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Initialize a StringBuffer.'
                },
                {
                    label: "Math.pow",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Math.pow(${1:base}, ${2:exponent})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Raise a number to a power.'
                },
                {
                    label: "Math.sqrt",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Math.sqrt(${1:number})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Calculate the square root.'
                },
                {
                    label: "Thread initialization",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Thread ${1:thread} = new Thread(() -> {\n\t$0\n});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Initialize a new Thread using a lambda expression.'
                },
                {
                    label: "Runnable implementation",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Runnable ${1:runnable} = () -> {\n\t$0\n};',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a Runnable with a lambda.'
                },
                {
                    label: "Callable implementation",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Callable<${1:Type}> ${2:callable} = () -> {\n\treturn $0;\n};',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a Callable with a lambda.'
                },
                {
                    label: "Future declaration",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Future<${1:Type}> ${2:future} = ${3:executor}.submit(() -> {\n\treturn $0;\n});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Submit a Callable task to an executor and obtain a Future.'
                },
                {
                    label: "synchronized method",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'public synchronized void ${1:methodName}() {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Define a synchronized method.'
                },
                {
                    label: "volatile keyword",
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'volatile',
                    documentation: 'Volatile keyword for variables.'
                },
                {
                    label: "enum constant",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:CONSTANT_NAME}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Enum constant (usually declared in an enum).'
                },
                {
                    label: "switch-case with break",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'switch (${1:variable}) {\n\tcase ${2:constant}:\n\t\t$0\n\t\tbreak;\n\tdefault:\n\t\tbreak;\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Switch statement with break.'
                },
                {
                    label: "Lambda expression",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '(${1:params}) -> { $0 }',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Lambda expression (Java 8+).'
                },
                {
                    label: "Stream API",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:collection}.stream()\n\t.filter(${2:predicate})\n\t.map(${3:mapper})\n\t.collect(Collectors.toList());',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Convert collection to stream, filter, map, and collect.'
                },
                {
                    label: "filter() method",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '.stream().filter(${1:predicate})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Apply filter to a stream.'
                },
                {
                    label: "map() method",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '.stream().map(${1:mapper})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Apply mapping to a stream.'
                },
                {
                    label: "collect() method",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '.stream().collect(Collectors.toList())',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Collect stream elements into a List.'
                },
                {
                    label: "Comparator.comparing",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Comparator.comparing(${1:KeyExtractor})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Creates a comparator using a key extractor function.'
                },
                {
                    label: "Optional.ofNullable",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Optional.ofNullable(${1:object})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Wrap an object in an Optional.'
                },
                {
                    label: "Optional.orElse",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Optional.ofNullable(${1:object}).orElse(${2:defaultValue})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Provide a default value if object is null.'
                },
                {
                    label: "Optional.ifPresent",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Optional.ofNullable(${1:object}).ifPresent(${2:consumer})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Perform action if object is not null.'
                },
                {
                    label: "Comparator.comparing (with reverseOrder)",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Comparator.comparing(${1:KeyExtractor}).reversed()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Creates a reversed comparator using a key extractor.'
                },
                {
                    label: "Objects.requireNonNull",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Objects.requireNonNull(${1:object})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Ensure object is not null.'
                },
                {
                    label: "List.of (immutable)",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'List.of(${1:element1}, ${2:element2}${3:, ...})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Creates an immutable list (Java 9+).'
                },
                {
                    label: "Set.of (immutable)",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Set.of(${1:element1}, ${2:element2}${3:, ...})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Creates an immutable set (Java 9+).'
                },
                {
                    label: "Map.of (immutable)",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Map.of(${1:key1}, ${2:value1}${3:, ...})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Creates an immutable map (Java 9+).'
                },
                {
                    label: "record (Java 16)",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'public record ${1:RecordName}(${2:fieldType fieldName, ...}) {}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Defines a record (immutable data carrier, Java 16+).'
                },
                {
                    label: "switch expression (Java 14+)",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'switch (${1:variable}) {\n\tcase ${2:constant} -> $0;\n\tdefault -> $3;\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Switch expression using arrow syntax (Java 14+).'
                },
                {
                    label: "Pattern.compile",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Pattern.compile("${1:regex}")',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Compile a regular expression.'
                },
                {
                    label: "Matcher matcher",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Matcher matcher = pattern.matcher(${1:string});\nif (matcher.find()) {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Find a pattern match in a string.'
                },
                {
                    label: "try-with-resources (AutoCloseable)",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'try (${1:Resource} ${2:res} = ${3:openResource}()) {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Try-with-resources block for AutoCloseable objects.'
                },
                {
                    label: "System.getProperty",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'System.getProperty("${1:propertyName}")',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get a system property.'
                },
                {
                    label: "System.setProperty",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'System.setProperty("${1:propertyName}", "${2:value}")',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Set a system property.'
                },
                {
                    label: "ternary operator",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:condition} ? ${2:ifTrue} : ${3:ifFalse}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Ternary operator for inline if-else.'
                },
                {
                    label: "Arrays.asList",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'List<${1:Type}> list = Arrays.asList(${2:elements});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Initialize a List using Arrays.asList.'
                },
                {
                    label: "Array initialization",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:Type}[] ${2:array} = new ${1:Type}[${3:size}];',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Initialize an array.'
                },
                {
                    label: "try-catch IOException",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'try {\n\t$0\n} catch (IOException e) {\n\te.printStackTrace();\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Try-catch block for IOException.'
                },
                {
                    label: "catch NullPointerException",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'catch (NullPointerException e) {\n\te.printStackTrace();\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Catch NullPointerException.'
                },
                {
                    label: "multi-catch block",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'try {\n\t$0\n} catch (IOException | SQLException e) {\n\te.printStackTrace();\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Try block with multi-catch for IOException and SQLException.'
                },
                {
                    label: "generic method",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'public <T> ${1:ReturnType} ${2:methodName}(T ${3:parameter}) {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Define a generic method.'
                },
                {
                    label: "@Override annotation",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '@Override\n$0',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Override a method from a superclass.'
                },
                {
                    label: "@Deprecated annotation",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '@Deprecated\n$0',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Mark a method or class as deprecated.'
                },
                {
                    label: "@SuppressWarnings annotation",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '@SuppressWarnings("${1:warning}")\n$0',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Suppress compiler warnings.'
                },
                {
                    label: "constructor",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'public ${1:ClassName}(${2:parameters}) {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Define a class constructor.'
                },
                {
                    label: "getter method",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'public ${1:Type} get${2:FieldName}() {\n\treturn this.${3:fieldName};\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Define a getter method.'
                },
                {
                    label: "setter method",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'public void set${1:FieldName}(${2:Type} ${3:fieldName}) {\n\tthis.${3:fieldName} = ${3:fieldName};\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Define a setter method.'
                },
                {
                    label: "toString method",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '@Override\npublic String toString() {\n\treturn "${1:ClassName}{" +\n\t\t"${2:field}=" + ${2:field} +\n\t\t"}";\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Override toString method.'
                },
                {
                    label: "equals method",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '@Override\npublic boolean equals(Object obj) {\n\tif (this == obj) return true;\n\tif (obj == null || getClass() != obj.getClass()) return false;\n\t${1:ClassName} other = (${1:ClassName}) obj;\n\t// Compare fields here\n\treturn true;\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Override equals method.'
                },
                {
                    label: "hashCode method",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '@Override\npublic int hashCode() {\n\treturn Objects.hash(${1:field1}, ${2:field2});\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Override hashCode method.'
                },
                {
                    label: "clone method",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '@Override\nprotected Object clone() throws CloneNotSupportedException {\n\treturn super.clone();\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Override clone method.'
                },
                {
                    label: "finalize method",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '@Override\nprotected void finalize() throws Throwable {\n\ttry {\n\t\t$0\n\t} finally {\n\t\tsuper.finalize();\n\t}\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Override finalize method.'
                },
                {
                    label: "static initializer block",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'static {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Static initializer block.'
                },
                {
                    label: "instance initializer block",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '{\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Instance initializer block.'
                },
                {
                    label: "inner class",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'class ${1:InnerClass} {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Define an inner class.'
                },
                {
                    label: "anonymous class",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new ${1:Type}() {\n\t$0\n}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create an anonymous class.'
                },
                {
                    label: "lambda comparator",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Comparator.comparing(${1:object} -> ${1:object}.${2:property})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Lambda expression for a comparator.'
                },
                {
                    label: "stream filter and collect",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:collection}.stream()\n\t.filter(${2:predicate})\n\t.collect(Collectors.toList());',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Stream filtering and collecting into a list.'
                },
                {
                    label: "stream forEach",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:list}.stream().forEach(${2:element} -> {\n\t$0\n});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Iterate over a list using forEach and a lambda expression.'
                },
                {
                    label: "Optional.map",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Optional.ofNullable(${1:object}).map(${2:mapper})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Map an Optional value if present.'
                },
                {
                    label: "throws declaration",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'throws ${1:Exception}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Declare that a method throws an exception.'
                },
                {
                    label: "Multi-line comment",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '/**\n * $0\n */',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Insert a multi-line comment.'
                },
                {
                    label: "Single-line comment",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '// $0',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Insert a single-line comment.'
                },
                // ---- Additional Items 101-200 ----
                {
                    label: "Integer.parseInt",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Integer.parseInt(${1:string})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Parse a string to an int.'
                },
                {
                    label: "Double.parseDouble",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Double.parseDouble(${1:string})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Parse a string to a double.'
                },
                {
                    label: "Boolean.parseBoolean",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Boolean.parseBoolean(${1:string})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Parse a string to a boolean.'
                },
                {
                    label: "Long.parseLong",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Long.parseLong(${1:string})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Parse a string to a long.'
                },
                {
                    label: "Float.parseFloat",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Float.parseFloat(${1:string})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Parse a string to a float.'
                },
                {
                    label: "Short.parseShort",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Short.parseShort(${1:string})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Parse a string to a short.'
                },
                {
                    label: "Byte.parseByte",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Byte.parseByte(${1:string})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Parse a string to a byte.'
                },
                {
                    label: "String.valueOf",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'String.valueOf(${1:object})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Convert an object to its string representation.'
                },
                {
                    label: "new Scanner",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Scanner ${1:sc} = new Scanner(System.in);',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Initialize a new Scanner for standard input.'
                },
                {
                    label: "sc.nextLine",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:sc}.nextLine()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Read a line from the Scanner.'
                },
                {
                    label: "sc.nextInt",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:sc}.nextInt()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Read an int from the Scanner.'
                },
                {
                    label: "sc.nextDouble",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:sc}.nextDouble()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Read a double from the Scanner.'
                },
                {
                    label: "sc.nextBoolean",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:sc}.nextBoolean()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Read a boolean from the Scanner.'
                },
                {
                    label: "sc.close",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:sc}.close();',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Close the Scanner.'
                },
                {
                    label: "String.substring",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:string}.substring(${2:start}, ${3:end})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Extract a substring from a string.'
                },
                {
                    label: "String.charAt",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:string}.charAt(${2:index})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get character at a specified index.'
                },
                {
                    label: "String.indexOf",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:string}.indexOf(${2:substring})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Find the first occurrence of a substring.'
                },
                {
                    label: "String.toUpperCase",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:string}.toUpperCase()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Convert string to uppercase.'
                },
                {
                    label: "String.toLowerCase",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:string}.toLowerCase()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Convert string to lowercase.'
                },
                {
                    label: "String.trim",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:string}.trim()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Trim whitespace from string.'
                },
                {
                    label: "String.replace",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:string}.replace(${2:old}, ${3:new})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Replace characters or substring in a string.'
                },
                {
                    label: "Arrays.sort",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Arrays.sort(${1:array});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Sort an array.'
                },
                {
                    label: "Arrays.toString",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Arrays.toString(${1:array})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Convert an array to a string.'
                },
                {
                    label: "Collections.sort",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Collections.sort(${1:list});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Sort a list.'
                },
                {
                    label: "Collections.reverse",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Collections.reverse(${1:list});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Reverse the order of a list.'
                },
                {
                    label: "Collections.shuffle",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Collections.shuffle(${1:list});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Shuffle a list randomly.'
                },
                {
                    label: "List.add",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:list}.add(${2:element});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Add an element to a list.'
                },
                {
                    label: "List.remove",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:list}.remove(${2:element});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Remove an element from a list.'
                },
                {
                    label: "Map.put",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:map}.put(${2:key}, ${3:value});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Put a key-value pair into a map.'
                },
                {
                    label: "Map.get",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:map}.get(${2:key});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get a value from a map using a key.'
                },
                {
                    label: "Map.containsKey",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:map}.containsKey(${2:key});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Check if a map contains a given key.'
                },
                {
                    label: "Map.containsValue",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:map}.containsValue(${2:value});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Check if a map contains a given value.'
                },
                {
                    label: "Map.remove",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:map}.remove(${2:key});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Remove an entry from a map.'
                },
                {
                    label: "Set.add",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:set}.add(${2:element});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Add an element to a set.'
                },
                {
                    label: "Set.remove",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: '${1:set}.remove(${2:element});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Remove an element from a set.'
                },
                {
                    label: "System.currentTimeMillis",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'System.currentTimeMillis()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get the current time in milliseconds.'
                },
                {
                    label: "System.nanoTime",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'System.nanoTime()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get the current time in nanoseconds.'
                },
                {
                    label: "Math.abs",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Math.abs(${1:number})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Absolute value of a number.'
                },
                {
                    label: "Math.max",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Math.max(${1:a}, ${2:b})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Maximum of two numbers.'
                },
                {
                    label: "Math.min",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Math.min(${1:a}, ${2:b})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Minimum of two numbers.'
                },
                {
                    label: "Math.random",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Math.random()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Generate a random number between 0 and 1.'
                },
                {
                    label: "Objects.equals",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Objects.equals(${1:a}, ${2:b})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Compare two objects for equality.'
                },
                {
                    label: "Objects.hash",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Objects.hash(${1:fields})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Generate hash code for given fields.'
                },
                {
                    label: "LocalDate.now",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'LocalDate.now()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get the current date.'
                },
                {
                    label: "LocalTime.now",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'LocalTime.now()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get the current time.'
                },
                {
                    label: "LocalDateTime.now",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'LocalDateTime.now()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get the current date and time.'
                },
                {
                    label: "DateFormat.getInstance",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'DateFormat.getInstance()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get the default date format.'
                },
                {
                    label: "new SimpleDateFormat",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new SimpleDateFormat("${1:pattern}")',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a new SimpleDateFormat with a given pattern.'
                },
                {
                    label: "Calendar.getInstance",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Calendar.getInstance()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get a calendar instance.'
                },
                {
                    label: "Thread.sleep",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Thread.sleep(${1:milliseconds});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Pause the current thread for a specified time.'
                },
                {
                    label: "Runtime.getRuntime",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Runtime.getRuntime()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get the runtime instance.'
                },
                {
                    label: "Runtime.exec",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Runtime.getRuntime().exec("${1:command}")',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Execute a system command.'
                },
                {
                    label: "System.gc",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'System.gc();',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Request garbage collection.'
                },
                {
                    label: "System.exit",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'System.exit(${1:status});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Terminate the JVM.'
                },
                {
                    label: "BufferedReader.readLine",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'bufferedReader.readLine()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Read a line from a BufferedReader.'
                },
                {
                    label: "new FileReader",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new FileReader("${1:filename}")',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a new FileReader for a given file.'
                },
                {
                    label: "new FileWriter",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new FileWriter("${1:filename}")',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a new FileWriter for a given file.'
                },
                {
                    label: "printWriter.println",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'printWriter.println(${1:message});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Print a line using a PrintWriter.'
                },
                {
                    label: "new File",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new File("${1:path}")',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a new File object.'
                },
                {
                    label: "Files.readAllBytes",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Files.readAllBytes(Paths.get("${1:path}"))',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Read all bytes from a file.'
                },
                {
                    label: "Files.write",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Files.write(Paths.get("${1:path}"), ${2:bytes})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Write bytes to a file.'
                },
                {
                    label: "Optional.empty",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Optional.empty()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Return an empty Optional.'
                },
                {
                    label: "Optional.of",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Optional.of(${1:object})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Return an Optional with a non-null value.'
                },
                {
                    label: "Optional.ofNullable",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Optional.ofNullable(${1:object})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Return an Optional that may hold a null value.'
                },
                {
                    label: "String.join",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'String.join(${1:delimiter}, ${2:elements})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Join strings using a delimiter.'
                },
                {
                    label: "String.format",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'String.format("${1:format}", ${2:args})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Format a string using a format string and arguments.'
                },
                {
                    label: "Objects.toString",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Objects.toString(${1:object})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Convert an object to its string representation.'
                },
                {
                    label: "Class.forName",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Class.forName("${1:ClassName}")',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Load a class dynamically.'
                },
                {
                    label: "Thread.currentThread",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Thread.currentThread()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Return the current thread.'
                },
                {
                    label: "Thread.interrupt",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Thread.currentThread().interrupt();',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Interrupt the current thread.'
                },
                {
                    label: "Thread.isAlive",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Thread.currentThread().isAlive()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Check if the current thread is alive.'
                },
                {
                    label: "Runtime.availableProcessors",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Runtime.getRuntime().availableProcessors()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Return the number of available processors.'
                },
                {
                    label: "Locale.getDefault",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Locale.getDefault()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get the default Locale.'
                },
                {
                    label: "Locale.setDefault",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Locale.setDefault(${1:newLocale});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Set the default Locale.'
                },
                {
                    label: "UUID.randomUUID",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'UUID.randomUUID()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Generate a random UUID.'
                },
                {
                    label: "BigDecimal",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new BigDecimal("${1:value}")',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a new BigDecimal.'
                },
                {
                    label: "BigInteger",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new BigInteger("${1:value}")',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a new BigInteger.'
                },
                {
                    label: "NumberFormat.getInstance",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'NumberFormat.getInstance()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get a general number format instance.'
                },
                {
                    label: "new DecimalFormat",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new DecimalFormat("${1:pattern}")',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a new DecimalFormat with a pattern.'
                },
                {
                    label: "System.lineSeparator",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'System.lineSeparator()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get the system-dependent line separator.'
                },
                {
                    label: "Runtime.maxMemory",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Runtime.getRuntime().maxMemory()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Return the maximum memory the JVM will attempt to use.'
                },
                {
                    label: "Runtime.totalMemory",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Runtime.getRuntime().totalMemory()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Return the total memory currently in use by the JVM.'
                },
                {
                    label: "Runtime.freeMemory",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'Runtime.getRuntime().freeMemory()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Return the free memory available in the JVM.'
                },
                {
                    label: "ProcessBuilder",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new ProcessBuilder(${1:command}).start()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a new ProcessBuilder and start the process.'
                },
                {
                    label: "InetAddress.getLocalHost",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'InetAddress.getLocalHost()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get the local host address.'
                },
                {
                    label: "new Socket",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new Socket("${1:host}", ${2:port})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a new Socket connecting to a host and port.'
                },
                {
                    label: "new ServerSocket",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new ServerSocket(${1:port})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a new ServerSocket listening on a port.'
                },
                {
                    label: "new URL",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new URL("${1:url}")',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a new URL object.'
                },
                {
                    label: "URLConnection",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new URL("${1:url}").openConnection()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Open a connection to a URL.'
                },
                {
                    label: "HttpURLConnection",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'HttpURLConnection connection = (HttpURLConnection) new URL("${1:url}").openConnection();',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create an HttpURLConnection.'
                },
                {
                    label: "BufferedInputStream",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new BufferedInputStream(${1:inputStream})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Wrap an input stream with a BufferedInputStream.'
                },
                {
                    label: "BufferedOutputStream",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new BufferedOutputStream(${1:outputStream})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Wrap an output stream with a BufferedOutputStream.'
                },
                {
                    label: "InputStreamReader",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new InputStreamReader(${1:inputStream})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create an InputStreamReader from an InputStream.'
                },
                {
                    label: "OutputStreamWriter",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'new OutputStreamWriter(${1:outputStream})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create an OutputStreamWriter from an OutputStream.'
                },
                {
                    label: "Files.copy",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Files.copy(${1:source}, ${2:target}, StandardCopyOption.REPLACE_EXISTING);',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Copy a file, replacing if it exists.'
                },
                {
                    label: "Files.move",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Files.move(${1:source}, ${2:target});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Move a file to a new location.'
                },
                {
                    label: "Files.delete",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'Files.delete(${1:path});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Delete a file.'
                },
                {
                    label: "System.getenv",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'System.getenv("${1:variable}")',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get an environment variable.'
                },
                {
                    label: "System.getenvAll",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'System.getenv()',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Get all environment variables.'
                },
                {
                    label: "Calendar.setTime",
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'calendar.setTime(${1:date});',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Set the calendar time to the specified date.'
                }
            ];

            return {suggestions: suggestions};
        }
    });

}

// If you are not using modules, expose the function globally
window.registerJavaCompletions = registerJavaCompletions;
