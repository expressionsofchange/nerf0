from datastructure import TreeNode, TreeText

pp_test = TreeNode([
    TreeText("if"),
    TreeNode([
        TreeText("="),
        TreeText('1'),
        TreeText('2'),
    ]),
    TreeNode([
        TreeNode([
            TreeText("+"),
            TreeText('23'),
            TreeText("34"),
        ]),
        TreeText('1'),
        TreeNode([
            TreeText("+"),
            TreeText('uro sign (€) is the cu'),
            TreeText("14"),
        ]),
        TreeText("foo"),
    ]),
    TreeNode([
        TreeText("list"),
        TreeText('3'),
        TreeNode([
            TreeText("+"),
            TreeText('7'),
            TreeText("8"),
        ]),
        TreeText("bar"),
    ]),
])
