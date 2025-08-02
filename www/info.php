<?php
phpinfo();
echo '<br/>';
echo 'PHP version: ' . phpversion();
echo '<br/>';
echo 'PHP extensions: ' . implode(', ', get_loaded_extensions());