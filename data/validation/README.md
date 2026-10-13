# Body-shape validation set

Use this folder to check (and tune) the body-shape classifier on real people.

1. Take a **front-facing, full-body** photo of each volunteer (aim for at least 20 people, a few of each shape).
   Stand about 2-3 m from the camera, feet together, **arms slightly away from the sides**, plain background, fitted clothes.
2. Put the photos in `data/validation/photos/`.
3. Create `data/validation/labels.csv` with the label you agree on (for example from a tape measure, using
   the chest/waist/hip rule you will describe in the report):

       filename,label
       volunteer01.jpg,hourglass
       volunteer02.jpg,pear

   Labels: `hourglass`, `rectangle`, `inverted_triangle`, `pear`.
4. Run `python -m cv_vto.evaluate_shapes` for accuracy and a confusion matrix, and
   `python -m cv_vto.evaluate_shapes --tune` to see which thresholds fit your labelled set best.

Do not commit photos of people without their permission.
