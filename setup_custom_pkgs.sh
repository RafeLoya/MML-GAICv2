export LD_LIBRARY_PATH=/mnt/c/Users/RL/PycharmProjects/Grid-Anchor-based-Image-Cropping-Pytorch/venv/lib/
python3.13/site-packages/torch/lib:$LD_LIBRARY_PATH

# Test after setting the path
python -c "import roi_align_api; print('roi_align_api: SUCCESS')"
python -c "import rod_align_api; print('rod_align_api: SUCCESS')"

echo "if not successful, make sure you compiled roi_align and rod_align with make_all.sh."
echo "if this doesn't work, run the export cmd above outside of this script."
