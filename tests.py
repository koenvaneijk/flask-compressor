# -*- coding: utf-8 -*-

"""
    Flask-Compressor test suite
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from __future__ import unicode_literals, absolute_import, division, \
    print_function
import os
import unittest
import flask
import tempfile
from flask_compressor import Compressor, Bundle, Asset, FileAsset, \
    CompressorException, JSBundle, CSSBundle
from flask_compressor.processors import DEFAULT_PROCESSORS


class ProcessorsTestCase(unittest.TestCase):
    def setUp(self):
        # initialize the flask app
        app = flask.Flask(__name__)
        app.config['TESTING'] = True
        compressor = Compressor(app)
        self.app = app
        self.compressor = compressor

        # our processor function
        def test_processor(content):
            return "FOOBAR" + str(content)
        self.test_processor = test_processor

    def test_default_processors(self):
        for processor in DEFAULT_PROCESSORS:
            self.compressor.get_processor(processor.__name__)

    def test_register_processor(self):
        self.compressor.register_processor(self.test_processor)
        self.compressor.get_processor(self.test_processor.__name__)
        self.assertRaises(
            CompressorException,
            self.compressor.register_processor,
            self.test_processor
        )
        self.compressor.register_processor(self.test_processor, replace=True)
        self.compressor.get_processor(self.test_processor.__name__)

    def test_register_named_processor(self):
        self.compressor.register_processor(self.test_processor)
        self.compressor.register_processor(self.test_processor, 'test1')
        self.compressor.register_processor(self.test_processor, 'test2')
        self.assertRaises(
            CompressorException,
            self.compressor.register_processor,
            self.test_processor,
            'test1'
        )
        self.compressor.register_processor(
            self.test_processor,
            'test1',
            replace=True
        )
        self.compressor.get_processor(self.test_processor.__name__)
        self.compressor.get_processor('test1')
        self.compressor.get_processor('test2')

    def test_get_processor(self):
        self.compressor.register_processor(self.test_processor)
        self.compressor.register_processor(self.test_processor, 'test1')
        self.assertEqual(
            self.test_processor,
            self.compressor.get_processor('test1')
        )
        self.assertEqual(
            self.test_processor,
            self.compressor.get_processor(self.test_processor.__name__)
        )

    def test_processor_not_found(self):
        self.assertRaises(
            CompressorException,
            self.compressor.get_processor,
            self.test_processor.__name__,
        )
        self.compressor.register_processor(self.test_processor)
        self.compressor.get_processor(self.test_processor.__name__)

    def test_apply_processor(self):
        self.compressor.register_processor(self.test_processor, 'test')
        processor = self.compressor.get_processor('test')
        processed_content = processor('some garbage')
        self.assertEqual(processed_content, 'FOOBARsome garbage')


class CssminProcessorTestCase(unittest.TestCase):
    def setUp(self):
        # initialize the flask app
        app = flask.Flask(__name__)
        app.config['TESTING'] = True
        compressor = Compressor(app)
        self.app = app
        self.compressor = compressor

    def test_cssmin_is_present(self):
        self.compressor.get_processor('cssmin')

    def test_apply_cssmin(self):
        css_content = '''
            html {
                background-color: red;
            }
        '''
        processor = self.compressor.get_processor('cssmin')

        with self.app.test_request_context():
            processed_content = processor(css_content)
            self.assertEqual(processed_content, 'html{background-color:red}')


class BundlesTestCase(unittest.TestCase):
    def setUp(self):
        # initialize the flask app
        app = flask.Flask(__name__)
        app.config['TESTING'] = True
        compressor = Compressor(app)
        self.app = app
        self.compressor = compressor

        # our bundle
        bundle = Bundle(name='test_bundle')
        self.bundle = bundle

    def test_register_bundle(self):
        self.compressor.register_bundle(self.bundle)
        self.assertRaises(CompressorException, self.compressor.register_bundle,
                          self.bundle)
        self.compressor.register_bundle(self.bundle, replace=True)

    def test_get_bundle(self):
        self.compressor.register_bundle(self.bundle)
        bundle = self.compressor.get_bundle('test_bundle')
        self.assertEqual(bundle, self.bundle)

    def test_replace_bundle(self):
        self.compressor.register_bundle(self.bundle)
        self.compressor.register_bundle(self.bundle, replace=True)
        bundle = self.compressor.get_bundle('test_bundle')
        self.assertEqual(bundle, self.bundle)

    def test_bundle_not_found(self):
        self.assertRaises(CompressorException, self.compressor.get_bundle,
                          'test_bundle')
        self.compressor.register_bundle(self.bundle)
        self.compressor.get_bundle('test_bundle')
        self.assertRaises(CompressorException, self.compressor.get_bundle,
                          'WTF!')


class BundleWithAssetsTestCase(unittest.TestCase):
    def setUp(self):
        # initialize the flask app
        app = flask.Flask(__name__)
        app.config['TESTING'] = True
        compressor = Compressor(app)
        self.app = app
        self.compressor = compressor

        # some simple processors
        def test1(content):
            return "FOOBAR" + str(content)

        def test2(content):
            return str(content) + "BARFOO"

        compressor.register_processor(test1)
        compressor.register_processor(test2)

        # our bundle
        bundle = Bundle(
            name='test_bundle',
            assets=[
                Asset(content='first asset', processors=['test1']),
                Asset(content='second asset')
            ],
            processors=['test2']
        )
        self.bundle = bundle

        compressor.register_bundle(bundle)

    def test_get_content(self):
        bundle_content = 'FOOBARfirst asset\nsecond assetBARFOO'
        with self.app.test_request_context():
            content = self.bundle.get_content()
            self.assertEqual(content, bundle_content)

        bundle_content = 'FOOBARfirst asset\nsecond asset'
        with self.app.test_request_context():
            content = self.bundle.get_content(apply_processors=False)
            self.assertEqual(content, bundle_content)

    def test_get_contents(self):
        bundle_contents = ['FOOBARfirst assetBARFOO', 'second assetBARFOO']
        with self.app.test_request_context():
            contents = self.bundle.get_contents()
            self.assertEqual(contents, bundle_contents)

        bundle_contents = ['FOOBARfirst asset', 'second asset']
        with self.app.test_request_context():
            contents = self.bundle.get_contents(apply_processors=False)
            self.assertEqual(contents, bundle_contents)

    def test_get_inline_content(self):
        inline_content = 'FOOBARfirst asset\nsecond assetBARFOO'
        with self.app.test_request_context():
            content = self.bundle.get_inline_content()
            self.assertEqual(content, inline_content)

        inline_content = 'FOOBARfirst assetBARFOO\nsecond assetBARFOO'
        with self.app.test_request_context():
            contents = self.bundle.get_inline_content(concatenate=False)
            self.assertEqual(contents, inline_content)

    def test_get_linked_content(self):
        with self.app.test_request_context():
            linked_content = '<link ' \
                'ref="external" '\
                'href="/_compressor/bundle/test_bundle_v{}.txt" '\
                'type="text/plain">'.format(self.bundle.hash)
            content = self.bundle.get_linked_content()
            self.assertEqual(content, linked_content)

            linked_content = '<link ' \
                'ref="external" '\
                'href="/_compressor/bundle/test_bundle/asset/0_v{}.txt" ' \
                'type="text/plain">\n' \
                '<link '\
                'ref="external" ' \
                'href="/_compressor/bundle/test_bundle/asset/1_v{}.txt" ' \
                'type="text/plain">'.format(
                    self.bundle.assets[0].hash,
                    self.bundle.assets[1].hash
                )
            contents = self.bundle.get_linked_content(concatenate=False)
            self.assertEqual(contents, linked_content)

    def test_blueprint_urls(self):
        get = self.app.test_client().get

        with self.app.test_request_context():
            rv = get('/_compressor/bundle/test_bundle_v{}.txt'.format(
                self.bundle.hash
            ))
            self.assertEqual('FOOBARfirst asset\nsecond assetBARFOO',
                             rv.data.decode('utf8'))

            rv = get('/_compressor/bundle/bundle_not_found')
            self.assertEqual(rv.status_code, 404)

            rv = get('/_compressor/bundle/test_bundle/asset/0_v{}.txt'.format(
                self.bundle.assets[0].hash)
            )
            self.assertEqual('FOOBARfirst asset', rv.data.decode('utf8'))

            rv = get('/_compressor/bundle/test_bundle/asset/0_v{}.txt'.format(
                'wrong hash')
            )
            self.assertEqual(rv.status_code, 404)

            rv = get('/_compressor/bundle/test_bundle/asset/0.css')
            self.assertEqual(rv.status_code, 404)

            rv = get('/_compressor/bundle/test_bundle/asset/1_v{}.txt'.format(
                self.bundle.assets[1].hash
            ))
            self.assertEqual('second asset', rv.data.decode('utf8'))

            rv = get('/_compressor/bundle/test_bundle/asset/2.txt')
            self.assertEqual(rv.status_code, 404)

            rv = get('/_compressor/bundle/bundle_not_found/asset/0.txt')
            self.assertEqual(rv.status_code, 404)

    def test_cached_bundle_content(self):
        with self.app.test_request_context():
            evaluated_content = self.bundle.get_content()
            cached_content = self.bundle.get_content()
            self.assertEqual(evaluated_content, cached_content)


class AssetTestCase(unittest.TestCase):
    def setUp(self):
        # initialize the flask app
        app = flask.Flask(__name__)
        app.config['TESTING'] = True
        compressor = Compressor(app)
        self.app = app
        self.compressor = compressor

        self.css_content = '''
            html {
                background-color: red;
            }
        '''
        self.asset_processors = ['cssmin']
        self.asset = Asset(self.css_content, self.asset_processors)
        self.result_asset_content = 'html{background-color:red}'

    def test_raw_content(self):
        with self.app.test_request_context():
            self.assertEqual(self.asset.raw_content, self.css_content)

    def test_content(self):
        with self.app.test_request_context():
            self.assertEqual(self.result_asset_content, self.asset.content)


class FileAssetTestCase(AssetTestCase):
    def setUp(self):
        super(FileAssetTestCase, self).setUp()

        # create a temporary folder used as the 'static' folder of the Flask
        # application
        static_folder = tempfile.mkdtemp()
        self.static_folder = static_folder

        # initialize the flask app
        app = flask.Flask(__name__, static_folder=static_folder)
        app.config['TESTING'] = True
        compressor = Compressor(app)
        self.app = app
        self.compressor = compressor

        # create a temporary file
        fd, filename = tempfile.mkstemp(dir=static_folder)
        os.write(fd, self.css_content.encode('utf-8'))
        os.close(fd)
        self.filename = os.path.basename(filename)

        # create a FileAsset object
        self.asset = FileAsset(self.filename, self.asset_processors)

        bundle = Bundle(name='test_bundle', assets=[self.asset])
        self.bundle = bundle
        self.compressor.register_bundle(bundle)

    def tearDown(self):
        os.remove(os.path.join(self.static_folder, self.filename))
        os.removedirs(self.static_folder)

    def test_absolute_filename(self):
        with self.assertRaises(CompressorException) as cm:
            FileAsset('/tmp/foobar')

        self.assertIn('Absolute filename are not supported', str(cm.exception))

    def test_blueprint_urls(self):
        with self.app.test_request_context():
            get = self.app.test_client().get
            rv = get('/_compressor/bundle/test_bundle/asset/0_v{}.txt'
                     .format(self.bundle.hash))
            self.assertEqual(self.result_asset_content, rv.data.decode('utf8'))


class MultipleProcessorsTestCase(unittest.TestCase):
    def setUp(self):
        # initialize the flask app
        app = flask.Flask(__name__)
        app.config['TESTING'] = True
        compressor = Compressor(app)
        self.app = app
        self.compressor = compressor

        def processor1(content):
            return content.replace('html', ' body ')

        def processor2(content):
            return content.replace(' body ', 'p ')

        def processor3(content):
            return content.replace(':red}', ':blue}')

        self.compressor.register_processor(processor1)
        self.compressor.register_processor(processor2)
        self.compressor.register_processor(processor3)

        css_content = 'html { background-color: red; } '
        self.asset1 = Asset(css_content, processors=['processor1', 'processor2'])
        self.asset2 = Asset(css_content, processors=['processor2', 'processor1'])
        self.bundle = Bundle(
            'test_bundle',
            assets=[self.asset1, self.asset2],
            processors=['cssmin', 'processor3'],
        )

    def test_asset_content(self):
        asset_content = 'p  { background-color: red; } '
        with self.app.test_request_context():
            self.assertEqual(asset_content, self.asset1.content)

        asset_content = ' body  { background-color: red; } '
        with self.app.test_request_context():
            self.assertEqual(asset_content, self.asset2.content)

    def test_bundle_content(self):
        bundle_content = 'p{background-color:blue}body{background-color:blue}'
        with self.app.test_request_context():
            self.assertEqual(bundle_content, self.bundle.get_content())


class JSBundleTestCase(unittest.TestCase):
    def setUp(self):
        # initialize the flask app
        app = flask.Flask(__name__)
        app.config['TESTING'] = True
        compressor = Compressor(app)
        self.app = app
        self.compressor = compressor

        # our bundle
        bundle = JSBundle(
            name='test_bundle',
            assets=[
                Asset(content='first asset'),
                Asset(content='second asset'),
            ],
        )
        self.bundle = bundle

        compressor.register_bundle(bundle)

    def test_get_inline_content(self):
        inline_content = '<script type="text/javascript">first asset\nsecond asset</script>'
        with self.app.test_request_context():
            content = self.bundle.get_inline_content()
            self.assertEqual(content, inline_content)

        inline_content = '<script type="text/javascript">first asset</script>\n' \
            '<script type="text/javascript">second asset</script>'
        with self.app.test_request_context():
            contents = self.bundle.get_inline_content(concatenate=False)
            self.assertEqual(contents, inline_content)

    def test_get_linked_content(self):
        with self.app.test_request_context():
            linked_content = '<script type="text/javascript" ' \
                'src="/_compressor/bundle/test_bundle_v{}.js"></script>' \
                .format(
                    self.bundle.hash
                )
            content = self.bundle.get_linked_content()
            self.assertEqual(content, linked_content)

            linked_content = '<script type="text/javascript" ' \
                'src="/_compressor/bundle/test_bundle/asset/0_v{}.js">' \
                '</script>\n' \
                '<script type="text/javascript" ' \
                'src="/_compressor/bundle/test_bundle/asset/1_v{}.js">' \
                '</script>'.format(
                    self.bundle.assets[0].hash,
                    self.bundle.assets[1].hash
                )
            contents = self.bundle.get_linked_content(concatenate=False)
            self.assertEqual(contents, linked_content)


class CSSBundleTestCase(unittest.TestCase):
    def setUp(self):
        # initialize the flask app
        app = flask.Flask(__name__)
        app.config['TESTING'] = True
        compressor = Compressor(app)
        self.app = app
        self.compressor = compressor

        # our bundle
        bundle = CSSBundle(
            name='test_bundle',
            assets=[
                Asset(content='first asset'),
                Asset(content='second asset'),
            ],
        )
        self.bundle = bundle

        compressor.register_bundle(bundle)

    def test_get_inline_content(self):
        inline_content = '<style type="text/css">first asset\nsecond asset</style>'
        with self.app.test_request_context():
            content = self.bundle.get_inline_content()
            self.assertEqual(content, inline_content)

        inline_content = '<style type="text/css">first asset</style>\n' \
            '<style type="text/css">second asset</style>'
        with self.app.test_request_context():
            contents = self.bundle.get_inline_content(concatenate=False)
            self.assertEqual(contents, inline_content)

    def test_get_linked_content(self):
        with self.app.test_request_context():
            linked_content = '<link '\
                'type="text/css" rel="stylesheet" ' \
                'href="/_compressor/bundle/test_bundle_v{}.css">'.format(
                    self.bundle.hash
                )
            content = self.bundle.get_linked_content()
            self.assertEqual(content, linked_content)

            linked_content = '<link type="text/css" rel="stylesheet" ' \
                'href="/_compressor/bundle/test_bundle/asset/0_v{}.css">\n' \
                '<link type="text/css" rel="stylesheet" ' \
                'href="/_compressor/bundle/test_bundle/asset/1_v{}.css">' \
                .format(
                    self.bundle.assets[0].hash,
                    self.bundle.assets[1].hash
                )
            contents = self.bundle.get_linked_content(concatenate=False)
            self.assertEqual(contents, linked_content)


if __name__ == '__main__':
    unittest.main()
