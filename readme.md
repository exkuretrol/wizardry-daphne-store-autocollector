### Wizardry Daphne Store Autocollector

This is just a small bit of code to autocollect Wizardry Daphne weekly free rewards from the online store.

To execute, the imports need settled:

```
pip install selenium
```

Then execute `python main.py [your_Wizardry_ID]` on the command line.

This file should work across environments, locales, and operating systems; it just requires the Chrome webdriver. Should also be compatible with `cron` (see the GitHub Actions workflow for an example).