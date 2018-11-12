#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

"Blueprint for managing storage in the file system."

import hashlib
import os
from datetime import datetime
from os.path import abspath, dirname, exists, getmtime
from shutil import move
from uuid import uuid4

import tornado.gen

from thumbor.blueprints.storages import Storage


def plug_into_lifecycle():
    FileStorage()


class FileStorage(Storage):
    @classmethod
    @tornado.gen.coroutine
    def load_source_image(cls, request, details, image_url):
        "Loads source image from filesystem if it exists"
        file_abspath = cls._path_on_filesystem(details, image_url)

        if not exists(file_abspath):
            return

        with open(file_abspath, "rb") as source_file:
            details.source_image = source_file.read()

    @classmethod
    @tornado.gen.coroutine
    def save_source_image(cls, request, details, image_url, source_image):
        "Stores the source image in the filesystem"

        if source_image is None:
            return

        file_abspath = cls._path_on_filesystem(details, image_url)
        temp_abspath = "%s.%s" % (file_abspath, str(uuid4()).replace("-", ""))
        file_dir_abspath = dirname(file_abspath)

        cls._ensure_dir(file_dir_abspath)

        with open(temp_abspath, "wb") as _file:
            _file.write(source_image)

        move(temp_abspath, file_abspath)

        return

    @classmethod
    def _path_on_filesystem(cls, details, path):
        """Resolves the file in the filesystem"""
        digest = hashlib.sha1(path.encode("utf-8")).hexdigest()

        return "%s/%s/%s" % (
            details.config.FILE_STORAGE_ROOT_PATH.rstrip("/"),
            digest[:2],
            digest[2:],
        )

    @classmethod
    def _ensure_dir(cls, path):
        "Ensures the directory exists"

        if not exists(path):
            try:
                os.makedirs(path)
            except OSError as err:
                # FILE ALREADY EXISTS = 17

                if err.errno != 17:
                    raise

    @classmethod
    def _validate_path(cls, details, path):
        "Validates that the path starts with the root path"

        return abspath(path).startswith(
            details.config.RESULT_STORAGE_FILE_STORAGE_ROOT_PATH
        )

    @classmethod
    def _is_expired(cls, details, path):
        "Verifies if the file is expired"
        expire_in_seconds = details.config.get(
            "RESULT_STORAGE_EXPIRATION_SECONDS", None
        )

        if expire_in_seconds is None or expire_in_seconds == 0:
            return False

        timediff = datetime.now() - datetime.fromtimestamp(getmtime(path))

        return timediff.seconds > expire_in_seconds
