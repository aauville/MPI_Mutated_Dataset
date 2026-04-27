Steps to generate the dataset:

1. Install github-clone-all from https://github.com/rhysd/github-clone-all
2. Launch the command `github-clone-all -count 1000 -dest . 'MPI in:name,description,readme fork:false sort:stars'`
3. Install bear from https://github.com/rizsotto/Bear
4. Launch the command `chmod +x scraping.py`
5. Launch the command `./scraping.py (-h to see required options and details)`