library(testthat)
for (f in list.files("pipeline/R", full.names = TRUE)) source(f, encoding = "UTF-8")
test_dir("tests/testthat")
