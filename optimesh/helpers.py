# -*- coding: utf-8 -*-
#
import numpy
import fastfunc

import asciiplotlib as apl


def print_stats(mesh, extra_cols=None):
    extra_cols = [] if extra_cols is None else extra_cols

    angles = mesh.angles / numpy.pi * 180
    angles_hist, angles_bin_edges = numpy.histogram(
        angles, bins=numpy.linspace(0.0, 180.0, num=73, endpoint=True)
    )

    q = mesh.cell_quality
    q_hist, q_bin_edges = numpy.histogram(
        q, bins=numpy.linspace(0.0, 1.0, num=41, endpoint=True)
    )

    grid = apl.subplot_grid(
        (1, 4 + len(extra_cols)), column_widths=None, border_style=None
    )
    grid[0, 0].hist(angles_hist, angles_bin_edges, grid=[24], bar_width=1, strip=True)
    grid[0, 1].aprint("min angle:     {:7.3f}".format(numpy.min(angles)))
    grid[0, 1].aprint("avg angle:     {:7.3f}".format(60))
    grid[0, 1].aprint("max angle:     {:7.3f}".format(numpy.max(angles)))
    grid[0, 1].aprint("std dev angle: {:7.3f}".format(numpy.std(angles)))
    grid[0, 2].hist(q_hist, q_bin_edges, bar_width=1, strip=True)
    grid[0, 3].aprint("min quality: {:5.3f}".format(numpy.min(q)))
    grid[0, 3].aprint("avg quality: {:5.3f}".format(numpy.average(q)))
    grid[0, 3].aprint("max quality: {:5.3f}".format(numpy.max(q)))

    for k, col in enumerate(extra_cols):
        grid[0, 4 + k].aprint(col)

    grid.show()
    return


def stepsize_till_flat(x, v):
    """Given triangles and directions, compute the minimum stepsize t at which the area
    of at least one of the new triangles `x + t*v` is zero.
    """
    # <https://math.stackexchange.com/a/3242740/36678>
    x1x0 = x[:, 1] - x[:, 0]
    x2x0 = x[:, 2] - x[:, 0]
    #
    v1v0 = v[:, 1] - v[:, 0]
    v2v0 = v[:, 2] - v[:, 0]
    #
    a = v1v0[:, 0] * v2v0[:, 1] - v1v0[:, 1] * v2v0[:, 0]
    b = (
        v1v0[:, 0] * x2x0[:, 1]
        + x1x0[:, 0] * v2v0[:, 1]
        - v1v0[:, 1] * x2x0[:, 0]
        - x1x0[:, 1] * v2v0[:, 0]
    )
    c = x1x0[:, 0] * x2x0[:, 1] - x1x0[:, 1] * x2x0[:, 0]
    #
    alpha = b ** 2 - 4 * a * c
    i = (alpha >= 0) & (a != 0.0)
    sqrt_alpha = numpy.sqrt(alpha[i])
    t0 = (-b[i] + sqrt_alpha) / (2 * a[i])
    t1 = (-b[i] - sqrt_alpha) / (2 * a[i])
    return min(numpy.min(t0[t0 > 0]), numpy.min(t1[t1 > 0]))


def runner(
    get_new_points,
    mesh,
    tol,
    max_num_steps,
    omega=1.0,
    method_name=None,
    verbose=False,
    callback=None,
    step_filename_format=None,
    uniform_density=False,
    get_stats_mesh=lambda mesh: mesh,
):
    k = 0

    stats_mesh = get_stats_mesh(mesh)
    print("\nBefore:")
    print_stats(stats_mesh)
    if step_filename_format:
        stats_mesh.save(
            step_filename_format.format(k),
            show_coedges=False,
            show_axes=False,
            cell_quality_coloring=("viridis", 0.0, 1.0, False),
        )

    if callback:
        callback(k, mesh)

    # mesh.write("out0.vtk")
    mesh.flip_until_delaunay()
    # mesh.write("out1.vtk")

    while True:
        k += 1

        new_points = get_new_points(mesh)
        diff = omega * (new_points - mesh.node_coords)

        rho = stepsize_till_flat(
            mesh.node_coords[mesh.cells["nodes"]], diff[mesh.cells["nodes"]]
        )
        print(rho)
        # if rho < 1.0:
        #     diff *= rho * 0.99

        # print(mesh.node_coords[mesh.cells["nodes"][20]])
        # print(mesh.node_coords[mesh.cells["nodes"][208]])
        # print()

        # The code once checked here if the orientation of any cell changes and reduced
        # the step size if it did. Computing the orientation is unnecessarily costly
        # though and doesn't easily translate to shell meshes. Since orientation changes
        # cannot occur, e.g., with CPT, advise the user to apply a few steps of a robust
        # smoother first (CPT) if the method crashes, or use relaxation.
        mesh.node_coords += diff
        # mesh.write("out2.vtk")
        mesh.update_values()
        mesh.flip_until_delaunay()
        # mesh.write("out3.vtk")
        # exit(1)

        # Abort the loop if the update was small
        is_final = (
            numpy.all(numpy.einsum("ij,ij->i", diff, diff) < tol ** 2)
            or k >= max_num_steps
        )

        if verbose or is_final or step_filename_format:
            stats_mesh = get_stats_mesh(mesh)
            if verbose and not is_final:
                print("\nstep {}:".format(k))
                print_stats(stats_mesh)
            elif is_final:
                info = "{} steps".format(k)
                if method_name is not None:
                    if abs(omega - 1.0) > 1.0e-10:
                        method_name += ", relaxation parameter {}".format(omega)
                    info += " of " + method_name

                print("\nFinal ({}):".format(info))
                print_stats(stats_mesh)
            if step_filename_format:
                stats_mesh.save(
                    step_filename_format.format(k),
                    show_coedges=False,
                    show_axes=False,
                    cell_quality_coloring=("viridis", 0.0, 1.0, False),
                )
        if callback:
            callback(k, mesh)

        if is_final:
            break

    return


def get_new_points_volume_averaged(mesh, reference_points):
    scaled_rp = (reference_points.T * mesh.cell_volumes).T

    new_points = numpy.zeros(mesh.node_coords.shape)
    for i in mesh.cells["nodes"].T:
        fastfunc.add.at(new_points, i, scaled_rp)

    omega = numpy.zeros(len(mesh.node_coords))
    for i in mesh.cells["nodes"].T:
        fastfunc.add.at(omega, i, mesh.cell_volumes)

    new_points /= omega[:, None]
    idx = mesh.is_boundary_node
    new_points[idx] = mesh.node_coords[idx]
    return new_points


def get_new_points_count_averaged(mesh, reference_points):
    # Estimate the density as 1/|tau|. This leads to some simplifcations: The new point
    # is simply the average of of the reference points (barycenters/cirumcenters) in the
    # star.
    new_points = numpy.zeros(mesh.node_coords.shape)
    for i in mesh.cells["nodes"].T:
        fastfunc.add.at(new_points, i, reference_points)

    omega = numpy.zeros(len(mesh.node_coords), dtype=int)
    for i in mesh.cells["nodes"].T:
        fastfunc.add.at(omega, i, numpy.ones(i.shape, dtype=int))

    new_points /= omega[:, None]
    idx = mesh.is_boundary_node
    new_points[idx] = mesh.node_coords[idx]
    return new_points
