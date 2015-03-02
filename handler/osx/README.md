# OS X `mediawiker://` application scheme handler

## Files
This directory contains two files (apart from this `README` file); 

### Application handler
Since OS X requires an Application to be a scheme handler, `Sublime Text Mediawiker Launcher.app` has been packaged for the sake of convenience. 

### Raw `.applescript` file
The raw, un-compiled `.applescript` file.

## Unsigned application trust
As the application is unsigned, this requires a deal of trust to run. To mitigate this, I here describe two ways to allay any uncertainty. They both require that you use the built-in `Apple Script Editor.app` in `/Applications/Utilities/`

### Open the compiled application
This will let you examine that the code is the same as the uncompiled code

### Compile a "clean" application bundle from the raw code
In the unlikely event that an exploit might exist that makes it possible to create an application that decompiles in Apple Script Editor to show something different from the actual source code, you can use the raw code to export your own Application bundle.

Open the `.applescript` file in Apple Script Editor and select File > Export, and select `Application`.