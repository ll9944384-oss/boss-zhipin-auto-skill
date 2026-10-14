on findBossTab(tabHint)
  tell application "Safari"
    set targetWindow to missing value
    set targetTab to missing value
    repeat with w in windows
      repeat with t in tabs of w
        set u to URL of t
        if u contains tabHint then
          set targetWindow to w
          set targetTab to t
          exit repeat
        end if
      end repeat
      if targetTab is not missing value then exit repeat
    end repeat
    if targetTab is missing value then error "No Safari tab matching " & tabHint
    return targetTab
  end tell
end findBossTab

on run argv
  set modeName to item 1 of argv

  if modeName is "tabs" then
    tell application "Safari"
      set o to ""
      repeat with w in windows
        repeat with t in tabs of w
          set r to ("[" & name of t & "] " & URL of t)
          if o is "" then
            set o to r
          else
            set o to (o & " | " & r)
          end if
        end repeat
      end repeat
      return o
    end tell
  end if

  if modeName is "navigate" then
    set targetUrl to item 2 of argv
    tell application "Safari"
      activate
      if (count of windows) = 0 then make new document
      set URL of document 1 to targetUrl
    end tell
    return "ok"
  end if

  if modeName is "bounds" then
    tell application "Safari"
      activate
      set b to bounds of front window
      return (item 1 of b as string) & "," & (item 2 of b as string) & "," & (item 3 of b as string) & "," & (item 4 of b as string)
    end tell
  end if

  if modeName is "js-file" then
    set jsPath to item 2 of argv
    set tabHint to item 3 of argv
    set jsSource to read (POSIX file jsPath) as «class utf8»
    tell application "Safari"
      set targetTab to my findBossTab(tabHint)
      set jsResult to do JavaScript jsSource in targetTab
      return jsResult
    end tell
  end if

  if modeName is "paste" then
    tell application "Safari" to activate
    delay 0.2
    tell application "System Events"
      keystroke "v" using command down
    end tell
    return "ok"
  end if

  if modeName is "enter" then
    tell application "Safari" to activate
    delay 0.2
    tell application "System Events"
      key code 36
    end tell
    return "ok"
  end if

  error "Unknown mode: " & modeName
end run
