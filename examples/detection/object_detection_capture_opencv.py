#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    TF-TRT Object detection with OpenCV.

    Copyright (c) 2020 Nobuo Tsukamoto

    This software is released under the MIT License.
    See the LICENSE file in the project root for more information.
"""

import argparse
import sys
import os
import time

import tensorflow as tf
from tensorflow.python.compiler.tensorrt import trt

import numpy as np

WINDOW_NAME = "Jetson Nano TF-TRT Object detection(OpenCV)"

def get_frozen_graph(graph_file):
    """ Read Frozen Graph file from disk.
    
        Args:
            graph_file: File path to tf-trt model path.

    """
    with tf.gfile.GFile(graph_file, "rb") as f:
        graph_def = tf.GraphDef()
        graph_def.ParseFromString(f.read())
    return graph_def

def ReadLabelFile(file_path):
    """ Function to read labels from text files.
    Args:
        file_path: File path to labels.
    """
    with open(file_path, "r") as f:
        lines = f.readlines()

    ret = {}
    for line in lines:
        pair = line.strip().split(maxsplit=1)
        ret[int(pair[0])] = pair[1].strip()
    return ret

def random_colors(N):
    """ Random color generator.
    """
    N = N + 1
    hsv = [(i / N, 1.0, 1.0) for i in range(N)]
    colors = list(map(lambda c: tuple(int(i * 255) for i in colorsys.hsv_to_rgb(*c)), hsv))
    random.shuffle(colors)
    return colors

def draw_rectangle(image, box, color, thickness=3):
    """ Draws a rectangle.
    Args:
        image: The image to draw on.
        box: A list of 4 elements (x1, y1, x2, y2).
        color: Rectangle color.
        thickness: Thickness of lines.
    """
    b = np.array(box).astype(int)
    cv2.rectangle(image, (b[0], b[1]), (b[2], b[3]), color, thickness)

def draw_caption(image, box, caption):
    """ Draws a caption above the box in an image.
    Args:
        image: The image to draw on.
        box: A list of 4 elements (x1, y1, x2, y2).
        caption: String containing the text to draw.
    """
    b = np.array(box).astype(int)
    cv2.putText(image, caption, (b[0], b[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(image, caption, (b[0], b[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1)

def main():
    # parse args.
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='File path of tf-trt model.', required=True)
    parser.add_argument('--width', help='Input width.', default=640, type=int)
    parser.add_argument('--height', help='Input height.', default=480, type=int)
    parser.add_argument("--videopath", help="File path of Videofile.", default="")
    args = parser.parse_args()

    # Initialize window.
    cv2.namedWindow(
        WINDOW_NAME, cv2.WINDOW_GUI_NORMAL | cv2.WINDOW_AUTOSIZE | cv2.WINDOW_KEEPRATIO
    )
    cv2.moveWindow(WINDOW_NAME, 100, 200)

    # Read label file and generate random colors.
    labels = ReadLabelFile(args.label) if args.label else None
    last_key = sorted(labels.keys())[len(labels.keys()) - 1]
    colors = visual.random_colors(last_key)

    # Load graph.
    tf.reset_default_graph()

    graph = get_frozen_graph(args.model)
    tf_config = tf.ConfigProto()
    tf_config.gpu_options.allow_growth = True
    tf_sess = tf.Session(config=tf_config)
    tf.import_graph_def(graph, name='')

    input_names = ['image_tensor']
    tf_input = tf_sess.graph.get_tensor_by_name(input_names[0] + ':0')
    tf_scores = tf_sess.graph.get_tensor_by_name('detection_scores:0')
    tf_boxes = tf_sess.graph.get_tensor_by_name('detection_boxes:0')
    tf_classes = tf_sess.graph.get_tensor_by_name('detection_classes:0')
    tf_num_detections = tf_sess.graph.get_tensor_by_name('num_detections:0')

    # Video capture.
    if args.videopath == "":
        print('Open camera.')
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    else:
        print('Open videl file: ', args.videopath)
        cap = cv2.VideoCapture(args.videopath)

    elapsed_list = []

    while(cap.isOpened()):
        _, frame = cap.read()
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Run inference.        
        start_tm = time.time()
        scores, boxes, classes, num_detections = tf_sess.run([tf_scores, tf_boxes, tf_classes, tf_num_detections], feed_dict={
            tf_input: image[None, ...]
        })
        elapsed_ms = (time.time() - start_tm) * 1000

        # plot boxes exceeding score threshold
        for i in range(num_detections):
            # scale box to image coordinates
            box = boxes[i] * np.array([image.shape[0], image.shape[1], image.shape[0], image.shape[1]])

            # display rectangle
            draw_rectangle(frame, box, colors(classes[i]))

            # display class name and score
            caption = "{0}({1:.2f})".format(labels[classes[i]], scores[i])

        # Calc fps.
        elapsed_list.append(elapsed_ms)
        avg_text = ""
        if len(elapsed_list) > 100:
            elapsed_list.pop(0)
            avg_elapsed_ms = np.mean(elapsed_list)
            avg_text = " AGV: {0:.2f}ms".format(avg_elapsed_ms)

        # Display fps
        fps_text = "{0:.2f}ms".format(elapsed_ms)
        visual.draw_caption(frame, (10, 30), fps_text + avg_text)

        # display
        cv2.imshow(WINDOW_NAME, frame)
        if cv2.waitKey(10) & 0xFF == ord("q"):
            break

    # When everything done, release the window
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
