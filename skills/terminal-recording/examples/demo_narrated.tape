# Example: VHS tape file with AI narration macros
# Process with: python narrated_tape.py demo_narrated.tape --render --mix

Output demo.mp4
Set FontSize 18
Set Width 900
Set Height 500
Set Theme "Dracula"
Set Padding 20

# @voice eleven:adam

# @narrate:before "Welcome to this demo of our command line tool."

Type "echo 'Hello, World!'"
Enter
Sleep 1s

# @narrate:before "Let's explore the current directory."

Type "ls -la"
Enter
Sleep 2s

# @narrate:during "Watch as we create a new file with some content."

Type "echo 'This is a test file' > test.txt"
Enter
Type "cat test.txt"
Enter
Sleep 1s

# @narrate:after "The file was created successfully. Now let's clean up."

Type "rm test.txt"
Enter
Sleep 500ms

# @narrate:wait

# @narrate:before "Thanks for watching! Don't forget to like and subscribe."

Sleep 2s
